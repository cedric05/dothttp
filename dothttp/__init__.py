import functools
import logging
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from http.cookiejar import LWPCookieJar
from typing import DefaultDict, Optional
from typing import Dict, List, Union

import jstyleson as json
from jsonschema import validate
from requests import PreparedRequest, Session, Response
# this is bad, loading private stuff. find a better way
from requests.status_codes import _codes as status_code
from textx import metamodel_from_file, TextXSyntaxError

from .curl_utils import to_curl
from .dsl_jsonparser import json_or_array_to_json
from .exceptions import *
from .exceptions import PropertyNotFoundException
from .parse_models import Allhttp
from .property_schema import property_schema

try:
    import magic
except ImportError:
    magic = None

FORM_URLENCODED = "application/x-www-form-urlencoded"

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
    properties: List[str]
    env: list
    debug: bool
    file: str
    info: bool
    no_cookie: bool
    format: bool
    stdout: bool = False
    experimental: bool = False
    target: str = field(default_factory=lambda: '1')


@dataclass
class Payload:
    data: Optional[Union[str, bytes, Dict]] = None
    json: Optional[Dict] = None
    header: Optional[str] = None
    filename: str = None
    # [[ "key", ["filename", "content", "datatype"],
    #  ["key",  ["filename2", "content", "datatype"]],
    #  ["key2",  [None, "content", "datatype"]],]
    files: Optional[List[List]] = None


@dataclass
class HttpDef:
    name: str = None
    method: str = None
    url: str = None
    headers: dict = None
    query: dict = None
    auth: tuple[str] = None
    payload: Optional[Payload] = None
    output: str = None


@dataclass
class Property:
    text: List = field(default_factory=list())
    key: Union[str, None] = None
    value: Union[str, None] = None


# noinspection PyPackageRequirements
class BaseModelProcessor:
    var_regex = re.compile(r'{{(?P<var>.*?)}}')

    def load_properties_n_headers(self):
        """
            1. in most scenarios, dev might want to short circut creating property file, but will wanted it as argument
                for those scenarios, user can define property's default value in http file itself.
                but there is a catch. if dev users same property twice, and passes different value,
                it would complicate scenario
            2. dev might want to separate property to a file. properties can be segregated in to multiple environments and dev
                can enable multiple at a time.  ('*' section exists, it will be by default used)
            3. dev can always mention which property file to load. but when he is lazy,
                he can define a `.dothttp.json` which will be loaded if dev didn't mention property file
            preference:
            command line property > property from file > default property
            property file syntax
            {
                "headers": {
                    "Content-Type": "application/json",
                },
                "*": {
                    "param1": "val1",
                    "param2": "val2",
                },
                "env1": {
                    "param1": "val3",
                    "param2": "val4",
                }
                // ....
            }
            currently environment has restriction to not use "*" and "headers"
        :return:
        """
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
                try:
                    validate(instance=props, schema=property_schema)
                except Exception as e:
                    base_logger.error(f'property json schema validation failed! ', exc_info=True)
                    raise PropertyFileException(message="property file has invalid json schema",
                                                file=self.property_file)

        else:
            props = {}
        self.default_headers.update(props.get('headers', {}))
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
        # dev can define default headers, which dev dont want to do it for all requests
        # in most scenarios, headers are either computed or common across all other requests
        # best syntax would be headers section of property file will define default headers
        self.default_headers = {}
        self.property_file = args.property_file
        self.env = args.env
        self.content = ''
        self.original_content = self.content = ''
        self.load()

    def load(self):
        self.load_content()
        self.load_model()
        self.load_properties_n_headers()
        self.load_command_line_props()
        self.validate_names()
        self.load_props_needed_for_content()
        self.select_target()

    def load_command_line_props(self):
        for prop in self.args.properties:
            try:
                key, value = prop.split("=")
                base_logger.debug(f"detected command line property {key} value: {value}")
                self.command_line_props[key] = value
            except:
                raise CommandLinePropError(prop=prop)

    def load_model(self):
        # textx has provided utility to load model metamodel.model_from_file(args.file)
        # but we had variable options, and it has to be dynamically populated
        try:
            model = dothttp_model.model_from_str(self.content)
        except TextXSyntaxError as e:
            raise HttpFileSyntaxException(file=self.file, message=e.args)
        except Exception as e:
            raise HttpFileException(message=e.args)
        self.model: Allhttp = model

    def load_content(self):
        if not os.path.exists(self.file):
            raise HttpFileNotFoundException(file=self.file)
        with open(self.file, 'r') as f:
            self.original_content = self.content = f.read()

    @staticmethod
    def validate_n_gen(prop, cache: Dict[str, Property]):
        p: Union[Property, None] = None
        if '=' in prop:
            key_values = prop.split('=')
            if len(key_values) != 2:
                raise HttpFileException(message='default property should not have multiple `=`')
            key, value = key_values
            # strip white space for keys
            key = key.strip()

            # strip white space for values
            value = value.strip()
            if value and value[0] == value[-1] and value[0] in {"'", '"'}:
                # strip "'" "'" if it has any
                # like ranga=" ramprasad" --> we should replace with " ramprasad"
                value = value[1:-1]
            if key in cache:
                if cache[key].value and value != cache[key].value:
                    raise HttpFileException(
                        message=f'property: `{key}` is defaulted with two/more different values, panicked ')
                p = cache[key]
                p.text.append(prop)
                p.value = value
            else:
                p = Property([prop], key, value)
            cache.setdefault(key, p)
        else:
            if prop in cache:
                cache[prop].text.append(prop)
            else:
                p = Property([prop])
                cache.setdefault(prop, p)
        return p

    def get_most_possible_val(self, var):
        args = self.command_line_props.get(var), self.properties.get(var), self.prop_cache[var].value
        for arg in args:
            if arg is not None:
                return arg

    def get_updated_content(self, content) -> str:
        """
            1. properties defined in file itself ({{a=10}})
                allowed values are
                {{ a=ranga}} {{a=ranga }} {{ a=ranga }} {{ a="ranga" }} {{ a='ranga' }}
                a=ranga for all above
                {{ a="ranga "}}
                in above case whitespace is considered
            2. properties from command line
            3. properties from file's activated env
            4. properties from files's '*'
        :return:
        """
        prop_cache = self.prop_cache

        content_prop_needed = self.get_declared_props(content)
        props_needed = set(content_prop_needed.keys())

        missing_props = props_needed - self.get_props_available()
        if len(missing_props) != 0:
            raise PropertyNotFoundException(
                var=missing_props, propertyfile=self.property_file if self.property_file else "not specified")
        for var in props_needed:
            # command line props take preference
            value = self.get_most_possible_val(var)
            base_logger.debug(f'using `{value}` for property {var}')
            for text_to_replace in content_prop_needed[var].text:
                content = content.replace("{{" + text_to_replace + "}}", value)
        return content

    @functools.lru_cache
    def get_props_available(self):
        return set(self.properties.keys()).union(set(self.command_line_props.keys())).union(set(
            key for key in self.prop_cache if self.prop_cache[key].value is not None))

    def load_props_needed_for_content(self):
        self.prop_cache = self.get_declared_props(self.content)

    def get_declared_props(self, content):
        out = BaseModelProcessor.var_regex.findall(content)
        base_logger.debug(f'property used in `{self.file}` are `{out}`')
        prop_cache: Dict[str, Property] = {}
        tuple(self.validate_n_gen(x, prop_cache) for x in out if x)  # generates prop_cache, this could be done better
        return prop_cache

    def select_target(self):
        if target := self.args.target:
            if not isinstance(target, str):
                target = str(target)
            if target.isdecimal():
                if 1 <= int(target) <= len(self.model.allhttps):
                    self.http = self.model.allhttps[int(target) - 1]
                else:
                    raise ParameterException(message="target startswith 1", key='target',
                                             value=target)
            else:
                try:
                    # if multiple names have same value, it will create confusion
                    # if they want to go with that. then pass id
                    self.http = next(filter(lambda http: http.namewrap.name == target,
                                            (http for http in self.model.allhttps if http.namewrap)))
                except StopIteration:
                    raise ParameterException(message="target is not spelled correctly", key='target',
                                             value=target)
        else:
            self.http = self.model.allhttps[0]

    def validate_names(self):
        names = []
        for index, http in enumerate(self.model.allhttps):
            name = http.namewrap.name if http.namewrap else str(index + 1)
            if name in names:
                raise HttpFileException(message=f"target: `{name}` appeared twice or more. panicked while processing")
            names.append(name)
            names.append(str(index + 1))


class RequestBase(BaseModelProcessor):
    def __init__(self, args: Config):
        super().__init__(args)
        self._cookie: Union[LWPCookieJar, None] = None
        self.httpdef = HttpDef()
        self._loaded = False

    def load_query(self):
        params: DefaultDict[List] = defaultdict(list)
        for line in self.http.lines:
            if query := line.query:
                params[self.get_updated_content(query.key)].append(self.get_updated_content(query.value))
        request_logger.debug(
            f'computed query params from `{self.file}` are `{params}`')
        self.httpdef.query = params

    def load_headers(self):
        """
            entrypoints
                1. dev defines headers in http file
                2. dev defines headers in property file
                3. dev defines headers via basic auth (only for Authorization)
                4. dev can define in data/file/files's type attribute section for ('content-type')
        :return:
        """
        headers = {}
        headers.update(self.default_headers)
        for line in self.http.lines:
            if header := line.header:
                headers[self.get_updated_content(header.key)] = self.get_updated_content(header.value)
        request_logger.debug(
            f'computed query params from `{self.file}` are `{headers}`')
        self.httpdef.headers = headers

    def load_url(self):
        request_logger.debug(
            f'url is {self.http.urlwrap.url}')
        self.httpdef.url = self.get_updated_content(self.http.urlwrap.url)

    def load_method(self):
        if method := self.http.urlwrap.method:
            request_logger.debug(
                f'method defined in `{self.file}` is {method}')
            self.httpdef.method = method
            return
        request_logger.debug(
            f'method not defined in `{self.file}`. defaults to `GET`')
        self.httpdef.method = "GET"

    def load_payload(self):
        self.httpdef.payload = self._load_payload()

    def _load_payload(self):
        """
            1. dev can define data with string
            2. dev can define data with json (will be sent as form)
            3. dev can define a file upload (will be sent as file upload)
            4. dev can define a json payload (will be sent as json string as payload)
            5. dev can define multipart
                5.1 dev can define file upload (header also optional)
                5.2 dev can define data input (header also, optional)
        :return:
        """
        # can be short circuted
        if not self.http.payload:
            return Payload()
        elif data := self.http.payload.data:
            content = self.get_updated_content(data)
            mimetype = self.get_mimetype_from_buffer(content,
                                                     self.get_updated_content(self.http.payload.type))
            request_logger.debug(
                f'payload for request is `{content}`')
            return Payload(content, header=mimetype)
        elif data_json := self.http.payload.datajson:
            d = json_or_array_to_json(data_json, self.get_updated_content)
            if isinstance(d, list):
                raise PayloadDataNotValidException(payload=f"data should be json/str, current: {d}")
            # TODO convert all into string
            # varstring hanlding
            return Payload(data=d, header=FORM_URLENCODED)
        elif upload_filename := self.http.payload.file:
            upload_filename = self.get_updated_content(upload_filename)
            request_logger.debug(
                f'payload will be loaded from `{upload_filename}`')
            if not os.path.exists(upload_filename):
                request_logger.debug(
                    f'payload file `{upload_filename}` Not found. ')
                raise DataFileNotFoundException(datafile=upload_filename)
            mimetype = self.get_mimetype_from_file(upload_filename, self.http.payload.type)
            with open(upload_filename, 'rb') as f:
                return Payload(data=f.read(), header=mimetype, filename=upload_filename)
        elif json_data := self.http.payload.json:
            d = json_or_array_to_json(json_data, self.get_updated_content)
            return Payload(json=d, header=MIME_TYPE_JSON)
        elif files_wrap := self.http.payload.fileswrap:
            files = []
            for multipart_file in files_wrap.files:
                multipart_content = self.get_updated_content(multipart_file.path)
                multipart_key = self.get_updated_content(multipart_file.name)
                mimetype = self.get_updated_content(multipart_file.type) if multipart_file.type else None
                if os.path.exists(multipart_content):  # probably check valid path, then check for exists
                    mimetype = self.get_mimetype_from_file(multipart_content, mimetype)
                    multipart_filename = os.path.basename(multipart_content)
                    multipart_content = open(multipart_content, 'rb')
                    files.append((multipart_key, (multipart_filename, multipart_content, mimetype)))
                else:
                    mimetype = self.get_mimetype_from_buffer(multipart_content, mimetype)
                    files.append((multipart_key, (None, multipart_content, mimetype)))
            return Payload(files=files)
        return Payload()

    @staticmethod
    def get_mimetype_from_file(filename, mimetype: Optional[str]) -> Optional[str]:
        if mimetype:
            return mimetype
        if magic:
            return magic.from_file(filename, mime=True)
        else:
            return None

    @staticmethod
    def get_mimetype_from_buffer(data, mimetype: Optional[str]) -> Optional[str]:
        if mimetype:
            return mimetype
        else:
            if magic:
                return magic.from_buffer(data, mime=True)
            else:
                return None

    def get_output(self):
        if output := self.http.output:
            output_file = self.get_updated_content(output.output)
            print(f'output will be written to `{os.path.abspath(output_file)}`')
            request_logger.debug(
                f'output will be written into `{self.file}` is `{os.path.abspath(output_file)}`')
            try:
                return open(output_file, 'wb')
            except Exception as e:
                request_logger.debug(
                    f'not able to open `{output}`. output will be written to stdout', exc_info=True)
                return sys.stdout
        else:
            return sys.stdout

    def get_cookie(self):
        """
            1. dev has option to not to save cookies
            2. it will come in handy for most scenarios, so until user explicitly says no, we will send
        :return:
        """
        if self.args.no_cookie:
            cookie = None
            request_logger.debug(f'cookies set to `{self.args.no_cookie}`')
        else:
            cookie = LWPCookieJar(DOTHTTP_COOKIEJAR)
            request_logger.debug(f'cookie {cookie} loaded from {DOTHTTP_COOKIEJAR}')
            try:
                if not os.path.exists(DOTHTTP_COOKIEJAR):
                    cookie.save()
                else:
                    cookie.load()
            except Exception as e:
                # mostly permission exception
                # traceback.print_exc()
                eprint("cookie save action failed")
                base_logger.debug("error while saving cookies", exc_info=True)
                cookie = None
                # FUTURE
                # instead of saving (short curiting here, could lead to bad logic error)
                self.args.no_cookie = True
        self._cookie = cookie
        return self._cookie

    def get_session(self):
        session = Session()
        if not self.args.no_cookie:
            if cookie := self.get_cookie():
                session.cookies = cookie
        # session.hooks['response'] = self.save_cookie_call_back
        return session

    def load_auth(self):
        if auth_wrap := self.http.basic_auth_wrap:
            self.httpdef.auth = self.get_updated_content(auth_wrap.username), self.get_updated_content(
                auth_wrap.password)

    def load_def(self):
        if self._loaded:
            return
        self.httpdef.name = self.args.target or '1'
        self.load_method()
        self.load_url()
        self.load_headers()
        self.load_query()
        self.load_payload()
        self.load_auth()
        self._loaded = True

    def get_request(self):
        prep = self.get_request_notbody()
        payload = self.httpdef.payload
        prep.prepare_body(data=payload.data, json=payload.json, files=payload.files)
        # prep.prepare_hooks({"response": self.save_cookie_call_back})
        if payload.header and CONTENT_TYPE not in prep.headers:
            # if content-type is provided by header
            # we will not wish to update it
            prep.headers[CONTENT_TYPE] = payload.header
        request_logger.debug(f'request prepared completely {prep}')
        return prep

    def get_request_notbody(self):
        self.load_def()
        prep = PreparedRequest()
        prep.prepare_url(self.httpdef.url, self.httpdef.query)
        prep.prepare_method(self.httpdef.method)
        prep.prepare_headers(self.httpdef.headers)
        prep.prepare_cookies(self.get_cookie())
        prep.prepare_auth(self.httpdef.auth, prep.url)
        return prep

    def run(self):
        raise NotImplementedError()


class CurlCompiler(RequestBase):

    def run(self):
        curl_req = self.get_curl_output()
        output = self.get_output()
        if 'b' in output.mode:
            curl_req = curl_req.encode()
        output.write(curl_req)
        if output.fileno() != 1:
            output.close()
        curl_logger.debug(f'curl request generation completed successfully')

    def get_curl_output(self):
        prep = self.get_request_notbody()
        parts = []
        payload = self.httpdef.payload
        if self.http.payload:
            if self.http.payload.file:
                parts.append(('--data', "@" + self.get_updated_content(self.http.payload.file)))
            elif self.http.payload.fileswrap:
                if payload.files:
                    for file in payload.files:
                        if isinstance(file[1][1], str):
                            parts.append(('--form', file[0] + "=" + file[1][1]))
                        else:
                            parts.append(('--form', file[0] + "=@" + file[1][1].name))
            else:
                prep.prepare_body(data=payload.data, json=payload.json, files=payload.files)
        curl_req = to_curl(prep, parts)
        return curl_req


class HttpFileFormatter(RequestBase):

    def get_updated_content(self, content):
        return content

    def load(self):
        self.load_content()
        self.load_model()
        self.prop_cache = {}

    @staticmethod
    def format(model):
        output_str = ""
        for http in model.allhttps:
            new_line = "\n"
            if namewrap := http.namewrap:
                output_str += f"@name(\"{namewrap.name}\"){new_line}"
            method = http.urlwrap.method if http.urlwrap.method else "GET"
            output_str += f'{method} "{http.urlwrap.url}"'
            if auth_wrap := http.basic_auth_wrap:
                output_str += f'{new_line}basicauth("{auth_wrap.username}", "{auth_wrap.password}")'
            if lines := http.lines:
                headers = new_line.join(map(lambda line: f'"{line.header.key}": "{line.header.value}"',
                                            filter(lambda line:
                                                   line.header, lines)))
                if headers:
                    output_str += f"\n{headers}"
                query = new_line.join(map(lambda line: f'? ("{line.query.key}", "{line.query.value}")',
                                          filter(lambda line:
                                                 line.query, lines)))
                if query:
                    output_str += f'\n{query}'
            if payload := http.payload:
                p = ""
                mime_type = payload.type
                if data := payload.data:
                    if '"' in data and "'" not in data:
                        data = f"'{data}'"
                    elif '"' not in data and "'" in data:
                        data = f'"{data}"'
                    else:
                        # TODO not completely works
                        # url escaping is done wrong
                        data = "'" + data.replace("'", "\\'") + "'"
                    p = f'data({data}{(" ," + mime_type) if mime_type else ""})'
                if datajson := payload.datajson:
                    parsed_data = json_or_array_to_json(datajson, lambda a: a)
                    p = f'data({json.dumps(parsed_data, indent=4)})'
                elif filetype := payload.file:
                    p = f'fileinput("{filetype}",{(" ," + mime_type) if mime_type else ""})'
                elif json_data := payload.json:
                    parsed_data = json_or_array_to_json(json_data, lambda a: a)
                    p = f'json({json.dumps(parsed_data, indent=4)})'
                elif files_wrap := payload.fileswrap:
                    p2 = ",\n\t".join(map(lambda
                                              file_type: f'("{file_type.name}", "{(file_type.path)}"'
                                                         f' , "{file_type.type}")' if file_type.type else ")",
                                          files_wrap.files))
                    p = f"files({new_line}\t{p2}{new_line})"
                output_str += f'{new_line}{p}'
            if output := http.output:
                output_str += f'{new_line}output({output.output})'
            output_str += new_line * 3
        return output_str

    def run(self):
        formatted = self.format(self.model)
        if self.args.stdout:
            print(formatted)
        else:
            with open(self.args.file, 'w') as f:
                f.write(formatted)


class RequestCompiler(RequestBase):

    def run(self):
        resp = self.get_response()
        self.print_req_info(resp.request)
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
        func = None
        if hasattr(output, 'mode') and 'b' in output.mode:
            func = lambda data: output.write(data)
        else:
            func = lambda data: output.write(data.decode())
        for data in resp.iter_content(1024):
            func(data)
        try:
            if output.fileno() != 1:
                output.close()
        except:
            request_logger.warning("not able to close, mostly happens while testing in pycharm")
            eprint("output file close failed")
        request_logger.debug(f'request executed completely')
        return resp

    def get_response(self):
        session = self.get_session()
        request = self.get_request()
        resp: Response = session.send(request)
        if not self.args.no_cookie and isinstance(session.cookies, LWPCookieJar):
            session.cookies.save()  # lwpCookie has .save method
        return resp

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
