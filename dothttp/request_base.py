import functools
import logging
import os
from http.cookiejar import LWPCookieJar
from typing import Union
from urllib.parse import urlparse, unquote, urlunparse

import jstyleson as json
from requests import PreparedRequest, Session, Response
# this is bad, loading private stuff. find a better way
from requests.auth import HTTPBasicAuth, HTTPDigestAuth
from requests.status_codes import _codes as status_code
from requests_pkcs12 import Pkcs12Adapter
from textx import metamodel_from_file

from dothttp import APPLICATION_JSON, MIME_TYPE_JSON, UNIX_SOCKET_SCHEME
from . import eprint, Config, HttpDefBase, js3py
from .curl_utils import to_curl
from .dsl_jsonparser import json_or_array_to_json
from .json_utils import JSONEncoder
from .parse_models import Allhttp
from .utils import quote_or_unquote

JSON_ENCODER = JSONEncoder(indent=4)

try:
    import magic
except ImportError:
    magic = None
try:
    import requests_unixsocket

    # will be able to make unix socket apis
    requests_unixsocket.monkeypatch()
except ImportError:
    # in wasm phase, it will not be available, and can be ignored
    pass

DOTHTTP_COOKIEJAR = os.path.expanduser('~/.dothttp.cookiejar')
base_logger = logging.getLogger("dothttp")
request_logger = logging.getLogger("request")
curl_logger = logging.getLogger("curl")

if os.path.exists(__file__):
    dir_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'http.tx')
else:
    dir_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'http.tx')
dothttp_model = metamodel_from_file(dir_path)


# noinspection PyPackageRequirements


def get_new_session():
    session = Session()
    if requests_unixsocket:
        from requests_unixsocket.adapters import UnixAdapter
        session.mount('http+unix://', UnixAdapter())
    return session


class RequestBase(HttpDefBase):
    global_session = get_new_session()

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
        if self.httpdef.session_clear:
            # calle should close session
            # TODO
            return get_new_session()
        session = self.global_session
        if not self.args.no_cookie:
            if cookie := self.get_cookie():
                session.cookies = cookie
        # session.hooks['response'] = self.save_cookie_call_back
        return session

    @functools.lru_cache
    def get_request(self):
        # httpdef has to be loaded
        # according to httpdef, prepared_request is built
        self.load_def()
        prep = self.httpdef.get_prepared_request()
        # cookie is separately prepared
        prep.prepare_cookies(self.get_cookie())
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
        prep = self.get_request()
        parts = []
        payload = self.httpdef.payload
        if auth := self.httpdef.auth:
            if isinstance(auth, HTTPDigestAuth):
                parts.append(("--digest", None))
                parts.append(("--user", f"{auth.username}:{auth.password}"))
            elif isinstance(auth, HTTPBasicAuth):
                parts.append(("--user", f"{auth.username}:{auth.password}"))
        if certificate := self.httpdef.certificate:
            parts.append(("--cert", f"{certificate[0]}"))
            if self.httpdef.certificate[1]:
                parts.append(("--key", f"{certificate[1]}"))
        elif p12 := self.httpdef.p12:
            # --cert-type P12 --cert cert.p12:password
            # https://stackoverflow.com/a/55890905
            parts.append(("--cert", f"{p12[0]}:{p12[1]}"))
            parts.append(("--cert-type", f"P12"))
        if self.httpdef.allow_insecure:
            parts.append(("-k", None))
        payload_parts = []
        if self.http.payload:
            if self.http.payload.file:
                payload_parts += [('--data', "@" + self.get_updated_content(self.http.payload.file))]
            elif self.http.payload.fileswrap:
                if payload.files:
                    for file in payload.files:
                        if isinstance(file[1][1], str):
                            payload_parts.append(('--form', file[0] + "=" + file[1][1]))
                        else:
                            payload_parts.append(('--form', file[0] + "=@" + file[1][1].name))
            elif self.http.payload.json:
                dumps = json.dumps(payload.json, indent=4)
                self.httpdef.headers['content-type'] = APPLICATION_JSON
                payload_parts += [('-d', dumps)]
            elif self.http.payload.data:
                if payload.header:
                    self.httpdef.headers['content-type'] = payload.header
                payload_parts += [('-d', payload.data)]
        # there few headers set dynamically
        # so set headers in the end
        for k, v in sorted(self.httpdef.headers.items()):
            parts += [('-H', '{0}: {1}'.format(k, v))]
        url = prep.url

        if url.startswith(UNIX_SOCKET_SCHEME):
            scheme, netloc, path, params, query, fragment = urlparse(url)
            unix_domain_socket_path = unquote(netloc)
            parts.append(("--unix-socket", unix_domain_socket_path))
            """
                >>urlparse.urlparse("http://some.page.pl/nothing.py;someparam=some;otherparam=other?query1=val1&query2=val2#frag")
                ParseResult(scheme='http', netloc='some.page.pl', path='/nothing.py', params='someparam=some;otherparam=other', query='query1=val1&query2=val2', fragment='frag')
            """
            # scheme will be changed to 'http:/'
            # netlock will be added by '--unix-socket /var/run/docker.sock'
            #
            url = urlunparse(["http", "localhost", path, params, query, fragment])

        parts += payload_parts
        curl_req = to_curl(url=url, method=prep.method, bodydata=parts)
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
            if getattr(http, "description", None):
                for line in http.description.splitlines():
                    output_str += "// " + line + new_line
                output_str += new_line
            if http.namewrap and http.namewrap.name:
                quote_type, name = quote_or_unquote(http.namewrap.name)
                output_str += f"@name({quote_type}{name}{quote_type}){new_line}"
            method = http.urlwrap.method if http.urlwrap.method else "GET"
            output_str += f'{method} "{http.urlwrap.url}"'
            if auth_wrap := http.authwrap:
                if basic_auth := auth_wrap.basic_auth:
                    output_str += f'{new_line}basicauth("{basic_auth.username}", "{basic_auth.password}")'
                elif digest_auth := auth_wrap.digest_auth:
                    output_str += f'{new_line}digestauth("{digest_auth.username}", "{digest_auth.password}")'
            if lines := http.lines:
                def check_for_quotes(line):
                    quote_type, value = quote_or_unquote(line.header.value)
                    return f'"{line.header.key}": {quote_type}{value}{quote_type}'

                headers = new_line.join(map(check_for_quotes, filter(lambda line: line.header, lines)))
                if headers:
                    output_str += f"\n{headers}"

                query = new_line.join(map(query_to_http,
                                          filter(lambda line:
                                                 line.query, lines)))
                if query:
                    output_str += f'\n{query}'
            if payload := http.payload:
                p = ""
                mime_type = payload.type
                if payload.data:
                    data = "".join([i.triple[3:-3] if i.triple else i.str for i in payload.data])
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
                    p = f'json({JSON_ENCODER.encode(parsed_data)})'
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


def query_to_http(line):
    quote_type = quote_or_unquote(line.query.value)[0]
    return f'? {quote_type}{line.query.key}{quote_type}= {quote_type}{line.query.value}{quote_type}'


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
        if self.httpdef.p12:
            session.mount(request.url,
                          Pkcs12Adapter(pkcs12_filename=self.httpdef.p12[0],
                                        pkcs12_password=self.httpdef.p12[1]))
        try:
            resp: Response = session.send(request, cert=self.httpdef.certificate,
                                          verify=not self.httpdef.allow_insecure)
        except UnicodeEncodeError:
            # for Chinese, smiley all other default encode converts into latin-1
            # as latin-1 didn't consist of those characters it will fail
            # in those scenarios, request will try to encode with utf-8
            # as a last resort, it may not be correct solution. may be it is.
            # for now proceeding with this
            request.prepare_body(request.body.encode("utf-8"), files=None)
            resp: Response = session.send(request, cert=self.httpdef.certificate,
                                          verify=not self.httpdef.allow_insecure)
        if not self.args.no_cookie and isinstance(session.cookies, LWPCookieJar):
            session.cookies.save()  # lwpCookie has .save method
        if self.httpdef.session_clear:
            session.close()
        return resp

    def execute_script(self, resp: Response):
        try:
            content_type = resp.headers.get('content-type', 'text/plain')
            # in some cases mimetype can have charset
            # like text/plain; charset=utf-8
            content_type = content_type.split(";")[0] if ';' in content_type else content_type
            return js3py.execute_script(
                is_json=content_type == MIME_TYPE_JSON,
                script=self.httpdef.test_script,
                status_code=resp.status_code,
                headers=dict(resp.headers),
                properties=self.property_util.get_all_properties_variables(),
                response_body_text=resp.text,
            )
        except Exception as e:
            request_logger.error(f"unknown exception {e} happened", e)

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
