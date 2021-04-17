import functools
import logging
import os
from http.cookiejar import LWPCookieJar
from typing import Union

import jstyleson as json
from requests import PreparedRequest, Session, Response
# this is bad, loading private stuff. find a better way
from requests.status_codes import _codes as status_code
from textx import metamodel_from_file

from dothttp.parse_models import Allhttp
from . import eprint, Config, HttpDefBase
from .curl_utils import to_curl
from .dsl_jsonparser import json_or_array_to_json

try:
    import magic
except ImportError:
    magic = None

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


# noinspection PyPackageRequirements


class RequestBase(HttpDefBase):
    global_session = Session()
    def __init__(self, args: Config):
        super().__init__(args)
        self._cookie: Union[LWPCookieJar, None] = None

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
        session = self.global_session
        if not self.args.no_cookie:
            if cookie := self.get_cookie():
                session.cookies = cookie
        # session.hooks['response'] = self.save_cookie_call_back
        return session

    @functools.lru_cache
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
    def format(model: Allhttp):
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
                query = new_line.join(map(lambda line: f'? "{line.query.key}"= "{line.query.value}"',
                                          filter(lambda line:
                                                 line.query, lines)))
                if query:
                    output_str += f'\n{query}'
            if payload := http.payload:
                p = ""
                mime_type = payload.type
                if payload.data or payload.multi:
                    data = payload.data or payload.multi[3:-3]
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
                                              file_type: f'("{file_type.name}", "{(file_type.path)}"' +
                                                         (f' , "{file_type.type}")' if file_type.type else ")"),
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
