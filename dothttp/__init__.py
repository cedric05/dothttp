import logging
import os
import re
import sys
from dataclasses import dataclass
from http.cookiejar import LWPCookieJar
from typing import Union, Dict, List

import jstyleson as json
import magic
from curlify import to_curl
from requests import PreparedRequest, Session, Response
# this is bad, loading private stuff. find a better way
from requests.status_codes import _codes as status_code
from textx import metamodel_from_file

from .dsl_jsonparser import json_or_array_to_json
from .exceptions import *
from .exceptions import PropertyNotFoundException

DOTHTTP_COOKIEJAR = os.path.expanduser('~/.dothttp.cookiejar')

MIME_TYPE_JSON = "application/json"

CONTENT_TYPE = 'content-type'

base_logger = logging.getLogger("dothttp")
request_logger = logging.getLogger("request")
curl_logger = logging.getLogger("curl")

if os.path.exists(__file__):
    dir_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'http.tx')
else:
    dir_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'http.tx')
dothttp_model = metamodel_from_file(dir_path)


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


@dataclass
class Config:
    curl: bool
    property_file: Union[str, None]
    propertys: List[str]
    env: list
    debug: bool
    file: str
    info: bool
    no_cookie: bool
    format: bool


@dataclass
class Payload:
    data: Union[str, bytes, None] = None
    json: Union[Dict, None] = None
    header: Union[str, None] = None
    files: Union[Dict, None] = None


class BaseModelProcessor:
    var_regex = re.compile(r'{(?P<varible>\w*)}')

    def load_properties(self):
        if not self.property_file:
            base_logger.debug('property file not specified')
            default = os.path.join(os.path.dirname(self.file), ".dothttp.json")
            if os.path.exists(default):
                base_logger.debug(
                    f'file: {default} exists. it will be used for property reference')
                self.property_file = default
        if self.property_file and not os.path.exists(self.property_file):
            base_logger.debug(
                f'file: {self.property_file} not found')
            raise PropertyFileNotFoundException(
                propertyfile=self.property_file)
        if self.property_file:
            with open(self.property_file, 'r') as f:
                try:
                    props = json.load(f)
                    base_logger.debug(
                        f'file: {self.property_file} loaded successfully')
                except Exception as e:
                    base_logger.error(f'exception loading property file ', exc_info=True)
                    raise PropertyFileNotJsonException(
                        propertyfile=self.property_file)
        else:
            props = {}
        self.properties.update(props.get("*", {}))
        if self.env:
            for env_name in self.env:
                self.properties.update(props.get(env_name, {}))
        return self.properties

    def __init__(self, args: Config):
        self.args = args
        self.file = args.file
        self.command_line_props = {}
        self.properties = {}
        self.property_file = args.property_file
        self.env = args.env
        self.content = ''
        self.original_content = self.content = ''
        self.load()

    def load(self):
        self.load_content()
        self.load_properties()
        self.load_command_line_props()
        self.update_content_with_prop()
        self.load_model()

    def load_command_line_props(self):
        for prop in self.args.propertys:
            try:
                key, value = prop.split("=")
                base_logger.debug(f"detected command line property {key} value: {value}")
                self.command_line_props[key] = value
            except:
                raise CommandLinePropError(prop)

    def load_model(self):
        # TODO for a very big file, it could be a problem
        # textx has provided utility to load model, but we had variable options
        # dothttp_model.model_from_file(args.file)
        try:
            model = dothttp_model.model_from_str(self.content)
        except:
            raise HttpFileSyntaxException(file=self.file, position=None)
        self.model = model

    def load_content(self):
        if not os.path.exists(self.file):
            raise HttpFileNotFoundException(file=self.file)
        with open(self.file, 'r') as f:
            self.original_content = self.content = f.read()

    def update_content_with_prop(self):
        out = BaseModelProcessor.var_regex.findall(self.content)
        base_logger.debug(f'property used in `{self.file}` are `{out}`')
        props_needed = set(filter(lambda x: x, out))
        keys = set(self.properties.keys()).union(set(self.command_line_props.keys()))
        missing_props = props_needed - keys
        if len(missing_props) != 0:
            raise PropertyNotFoundException(
                var=missing_props, propertyfile=self.property_file)
        for var in props_needed:
            base_logger.debug(
                f'using `{self.properties.get(var)}` for property {var} ')
            # command line props take preference
            value = self.command_line_props.get(var) or self.properties.get(var)
            self.content = re.sub(
                r'{%s}' % var, value, self.content)


class RequestBase(BaseModelProcessor):
    def __init__(self, args: Config):
        super().__init__(args)
        self._cookie: LWPCookieJar = None

    def get_query(self):
        params = {}
        for line in self.model.lines:
            if query := line.query:
                params[query.key] = query.value
        request_logger.debug(
            f'computed query params from `{self.file}` are `{params}`')
        return params

    def get_headers(self):
        headers = {}
        for line in self.model.lines:
            if header := line.header:
                headers[header.key] = header.value
        request_logger.debug(
            f'computed query params from `{self.file}` are `{headers}`')
        return headers

    def get_url(self):
        request_logger.debug(
            f'url is {self.model.http.url}')
        return self.model.http.url

    def get_method(self):
        if method := self.model.http.method:
            request_logger.debug(
                f'method defined in `{self.file}` is {method}')
            return method
        request_logger.debug(
            f'method not defined in `{self.file}`. defaults to `GET`')
        return "GET"

    def get_payload(self):
        # can be short circuted
        if not self.model.payload:
            return Payload()
        elif data := self.model.payload.data:
            mimetype = self.model.payload.type if self.model.payload.type else magic.from_buffer(data, mime=True)
            request_logger.debug(
                f'payload for request is `{data}`')
            return Payload(data, header=mimetype)
        elif filename := self.model.payload.file:
            request_logger.debug(
                f'payload will be loaded from `{filename}`')
            if not os.path.exists(filename):
                request_logger.debug(
                    f'payload file `{filename}` Not found. ')
                raise DataFileNotFoundException(datafile=filename)
            mimetype = self.model.payload.type if self.model.payload.type else magic.from_file(filename, mime=True)
            with open(filename, 'rb') as f:
                return Payload(data=f.read(), header=mimetype)
        elif json_data := self.model.payload.json:
            d = json_or_array_to_json(json_data)
            return Payload(json=d, header=MIME_TYPE_JSON)
        elif files_wrap := self.model.payload.fileswrap:
            files = {}
            for filetype in files_wrap.files:
                filename = filetype.name
                content = filetype.path
                mimetype = filetype.type
                if os.path.exists(filetype.path):  # probably check valid path, then check for exists
                    content = open(filetype.path, 'rb')
                    filename = os.path.basename(filetype.path)
                    if not mimetype: mimetype = magic.from_file(filetype.path, mime=True)
                elif not mimetype:
                    mimetype = magic.from_buffer(filetype.path, mime=True)
                files[filetype.name] = (filename, content, mimetype)
            return Payload(files=files)
        return Payload()

    def get_output(self):
        if output := self.model.output:
            request_logger.debug(
                f'output will be written into `{self.file}` is `{output}`')
            try:
                return open(output.output, 'wb')
            except:
                request_logger.debug(
                    f'not able to open `{output}`. output will be written to stdout')
                return sys.stdout
        else:
            return sys.stdout

    def get_cookie(self):
        if self.args.no_cookie:
            cookie = None
            request_logger.debug(f'cookies set to `{self.args.no_cookie}`')
        else:
            cookie = LWPCookieJar(DOTHTTP_COOKIEJAR)
            request_logger.debug(f'cookie {cookie} loaded from {DOTHTTP_COOKIEJAR}')
            if not os.path.exists(DOTHTTP_COOKIEJAR):
                cookie.save()
            else:
                cookie.load()
        self._cookie = cookie
        return self._cookie

    def get_session(self):
        session = Session()
        if not self.args.no_cookie:
            session.cookies = self.get_cookie()
        # session.hooks['response'] = self.save_cookie_call_back
        return session

    def get_auth(self):
        if auth_wrap := self.model.basic_auth_wrap:
            return auth_wrap.username, auth_wrap.password
        return None

    def get_request(self):
        prep = PreparedRequest()
        prep.prepare_url(self.get_url(), self.get_query())
        prep.prepare_method(self.get_method())
        prep.prepare_headers(self.get_headers())
        prep.prepare_cookies(self.get_cookie())
        prep.prepare_auth(self.get_auth(), prep.url)
        payload = self.get_payload()
        prep.prepare_body(data=payload.data, json=payload.json, files=payload.files)
        # prep.prepare_hooks({"response": self.save_cookie_call_back})
        if payload.header and CONTENT_TYPE not in prep.headers:
            # if content-type is provided by header
            # we will not wish to update it
            prep.headers[CONTENT_TYPE] = payload.header
        request_logger.debug(f'request prepared completely {prep}')
        return prep

    # remove me , i have no use
    def save_cookie_call_back(self, *_args, **_kwargs):
        base_logger.debug("in request cookie save phase")
        if self._cookie is not None:
            self._cookie.save()
            base_logger.debug(f"cookies saved to {DOTHTTP_COOKIEJAR}")

    def run(self):
        raise NotImplementedError()


class CurlCompiler(RequestBase):

    def run(self):
        prep = self.get_request()
        output = self.get_output()
        curl_req = to_curl(prep)
        if 'b' in output.mode:
            curl_req = curl_req.encode()
        output.write(curl_req)
        if output.fileno() != 1:
            output.close()
        curl_logger.debug(f'curl request generation completed successfully')


class HttpFileFormatter(RequestBase):

    def load(self):
        self.load_content()
        self.load_model()

    @staticmethod
    def format(model):
        new_line = "\n"
        output_str = f'{model.http.method} "{model.http.url}"'
        if auth_wrap := model.basic_auth_wrap:
            output_str += f'{new_line}basicauth("{auth_wrap.username}", "{auth_wrap.password}")'
        if lines := model.lines:
            headers = new_line.join(map(lambda line: f'"{line.header.key}": "{line.header.value}"',
                                        filter(lambda line:
                                               line.header, lines)))
            query = new_line.join(map(lambda line: f'? ("{line.query.key}", "{line.query.value}")',
                                      filter(lambda line:
                                             line.query, lines)))
            output_str += f'\n{headers}\n{query}'
        if payload := model.payload:
            p = ""
            mime_type = payload.type
            if data := payload.data:
                p = f'data("{data}", {mime_type})'
            elif filetype := payload.file:
                p = f'fileinput("{filetype}", {mime_type})'
            elif json_data := payload.json:
                parsed_data = json_or_array_to_json(json_data)
                p = f'json({json.dumps(parsed_data, indent=4)})'
            elif files_wrap := payload.fileswrap:
                p2 = "\n\t".join(map(
                    lambda file_type: f'("{file_type.name}", "{(file_type.name)}"'
                                      f', "{file_type.type}")'
                    , files_wrap.files))
                p = f"files(\n\t{p2}\n)"
            output_str += f'\n{p}'
        return output_str

    def run(self):
        formatted = self.format(self.model)
        with open(self.args.file, 'w') as f:
            f.write(formatted)


class RequestCompiler(RequestBase):

    def run(self):
        session = self.get_session()
        request = self.get_request()
        self.print_req_info(request)
        resp: Response = session.send(request)
        # FIXME issue with hooks, cookies aren't getting save while in hooks
        session.cookies.save()  # lwpCookie has .save method
        for hist_resp in resp.history:
            self.print_req_info(hist_resp, '<')
            request_logger.debug(
                f"server with url response {hist_resp}, status_code "
                f"{hist_resp.status_code}, url: {hist_resp.url}")
        if 400 <= resp.status_code:
            request_logger.error(f"server with url response {resp.status_code}")
            eprint(f"server responded with non 2XX code. code: {resp.status_code}")
        self.print_req_info(resp, '<')
        output = self.get_output()
        for data in resp.iter_content(1024):
            if 'b' in output.mode:
                output.write(data)
            else:
                output.write(data.decode())
        if output.fileno() != 1:
            output.close()
        request_logger.debug(f'request executed completely')

    def print_req_info(self, request: Union[PreparedRequest, Response], prefix=">"):
        if not (self.args.debug or self.args.info):
            return
        if hasattr(request, 'method'):
            print(f'{prefix} {request.method} {request.url}')
        else:
            print(f"{prefix} {request.status_code} {status_code[request.status_code][0].capitalize()}")
        for header in request.headers:
            print(f'{prefix} {header}: {request.headers[header]}')
        print('-------------------------------------------\n')
