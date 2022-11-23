import functools
import logging
import os
from http.cookiejar import LWPCookieJar
from pprint import pprint
from typing import Union
from urllib.parse import urlparse, unquote, urlunparse

import jstyleson as json
from requests import PreparedRequest, Session, Response
# this is bad, loading private stuff. find a better way
from requests.auth import HTTPBasicAuth, HTTPDigestAuth, CONTENT_TYPE_FORM_URLENCODED
from requests.status_codes import _codes as status_code
from requests_pkcs12 import Pkcs12Adapter
from textx import metamodel_from_file

from .js3py import ScriptResult
from . import APPLICATION_JSON, MIME_TYPE_JSON, UNIX_SOCKET_SCHEME, TEXT_PLAIN, CONTENT_TYPE
from . import eprint, Config, HttpDefBase, js3py, AWS4Auth
from .curl_utils import to_curl
from .dsl_jsonparser import json_or_array_to_json
from .json_utils import JSONEncoder
from .parse_models import Allhttp, Http, HttpFileType, ScriptType
from .utils import quote_or_unquote, apply_quote_or_unquote

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
    global_cookie_jar = None

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
            if RequestBase.global_cookie_jar:
                return RequestBase.global_cookie_jar
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
        RequestBase.global_cookie_jar = self._cookie = cookie
        return self._cookie

    def get_session(self):
        if self.httpdef.session_clear:
            # calle should close session
            # TODO
            return get_new_session()
        session = self.global_session
        # if not self.args.no_cookie:
        #     session.cookies = self.get_cookie()
        # session.hooks['response'] = self.save_cookie_call_back
        return session

    @functools.lru_cache
    def get_request(self):
        # httpdef has to be loaded
        # according to httpdef, prepared_request is built
        self.load_def()
        prep = self.httpdef.get_prepared_request()
        # cookie is separately prepared
        if not self.httpdef.session_clear:
            prep.prepare_cookies(self.get_cookie())
        else:
            prep.prepare_cookies({})
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
            elif isinstance(auth, AWS4Auth):
                for header_key, header_value in prep.headers.items():
                    # include only aws headers
                    if header_key.startswith("x-amz") or header_key.lower().startswith("authorization"):
                        parts += [('-H', '{0}: {1}'.format(header_key, header_value))]

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
            contenttype = None
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
                contenttype = APPLICATION_JSON
                payload_parts += [('-d', dumps)]
            elif self.http.payload.datajson:
                payload_parts += [('-d', prep.body)]
                contenttype = CONTENT_TYPE_FORM_URLENCODED
            else:
                payload_parts += [('-d', payload.data)]
                contenttype = TEXT_PLAIN
            if payload.header and contenttype and CONTENT_TYPE not in self.httpdef.headers:
                self.httpdef.headers['content-type'] = payload.header
        # there few headers which set dynamically (basically auth)
        # so set headers in the end
        # if isinstance(self.httpdef.headers, AWS4Auth):
        for k, v in sorted(self.httpdef.headers.items()):
            parts += [('-H', '{0}: {1}'.format(k, v))]

        if 'cookie' in prep.headers:
            parts += [('-H', '{0}: {1}'.format('cookie', prep.headers['cookie'] ))]

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
    def format_http(http: Http):
            output_str = ""
            new_line = "\n"
            if getattr(http, "description", None):
                for line in http.description.splitlines():
                    output_str += "// " + line + new_line
                output_str += new_line
            if http.namewrap and http.namewrap.name:
                quote_type, name = quote_or_unquote(http.namewrap.name)
                output_str += f"@name({quote_type}{name}{quote_type})"
                output_str += f" : {apply_quote_or_unquote(http.namewrap.base)}{new_line}" if http.namewrap.base else new_line
            if http.extra_args:
                for extra_arg in http.extra_args:
                    if extra_arg.clear:
                        output_str += f"@clear{new_line}"
                    if extra_arg.insecure:
                        output_str += f"@insecure{new_line}"
            method = http.urlwrap.method if http.urlwrap.method else "GET"
            output_str += f'{method} "{http.urlwrap.url}"'
            if certificate := http.certificate:
                if hasattr(certificate, "cert") and certificate.cert:
                    if certificate.cert and certificate.key:
                        output_str += f'{new_line}certificate(cert={apply_quote_or_unquote(certificate.cert)}, key={apply_quote_or_unquote(certificate.key)})'
                    elif certificate.cert:
                        output_str += f'{new_line}certificate(cert={apply_quote_or_unquote(certificate.cert)})'
                if hasattr(certificate, "p12_file") and certificate.p12_file:
                    if certificate.p12_file and certificate.password:
                        output_str += f'{new_line}p12(file={apply_quote_or_unquote(certificate.p12_file)}, password={apply_quote_or_unquote(certificate.password)})'
                    else:
                        output_str += f'{new_line}p12(file={apply_quote_or_unquote(certificate.p12_file)})'
            if auth_wrap := http.authwrap:
                if basic_auth := auth_wrap.basic_auth:
                    output_str += f'{new_line}basicauth("{basic_auth.username}", "{basic_auth.password}")'
                elif digest_auth := auth_wrap.digest_auth:
                    output_str += f'{new_line}digestauth("{digest_auth.username}", "{digest_auth.password}")'
                elif ntlm_auth := auth_wrap.ntlm_auth:
                    output_str += f'{new_line}ntlmauth("{ntlm_auth.username}", "{ntlm_auth.password}")'
                elif hawk_auth := auth_wrap.hawk_auth:
                    output_str += f'{new_line}hawkauth("{hawk_auth.hawk_id}", "{hawk_auth.key}", "{hawk_auth.algorithm}")'
                elif aws_auth := auth_wrap.aws_auth:
                    if aws_auth.service and aws_auth.region:
                        output_str += f'{new_line}awsauth(access_id="{aws_auth.access_id}", secret_key="{aws_auth.secret_token}", service="{aws_auth.service}", region="{aws_auth.region}")'
                    elif aws_auth.service:
                        output_str += f'{new_line}awsauth(access_id="{aws_auth.access_id}", secret_key="{aws_auth.secret_token}", service="{aws_auth.service}")'
                    else:
                        output_str += f'{new_line}awsauth(access_id="{aws_auth.access_id}", secret_key="{aws_auth.secret_token}" )'
            if lines := http.lines:
                def check_for_quotes(line):
                    quote_type, value = quote_or_unquote(line.header.value)
                    return f'"{line.header.key}": {quote_type}{value}{quote_type}'

                headers = new_line.join(map(check_for_quotes,
                                            filter(lambda
                                                       line: line.header and line.header.value and line.header.key and type(
                                                line.header.value) == str,
                                                   lines)))
                if headers:
                    output_str += f"\n{headers}"

                query = new_line.join(map(query_to_http,
                                          filter(lambda line:
                                                 line.query and type(line.query.value) == str, lines)))
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
                    p = f'text({data}{(" ," + mime_type) if mime_type else ""})'
                if datajson := payload.datajson:
                    parsed_data = json_or_array_to_json(datajson, lambda a: a)
                    p = f'urlencoded({json.dumps(parsed_data, indent=4)})'
                elif filetype := payload.file:
                    p = f'< "{filetype}"  {(" ;" + mime_type) if mime_type else ""}'
                elif json_data := payload.json:
                    parsed_data = json_or_array_to_json(json_data, lambda a: a)
                    p = f'json({JSON_ENCODER.encode(parsed_data)})'
                elif files_wrap := payload.fileswrap:
                    def function(multipart):
                        quote, _ = quote_or_unquote(multipart.path)
                        multipart_content_type = f' ; {quote}{multipart.type}{quote}' if multipart.type else ""
                        return f'{quote}{multipart.name}{quote} < {quote}{multipart.path}{quote}{multipart_content_type}'

                    p2 = ",\n\t".join(map(function,
                                          files_wrap.files))
                    p = f"multipart({new_line}\t{p2}{new_line})"
                output_str += f'{new_line}{p}'
            if output := http.output:
                output_str += f'{new_line}>> {output.output}'
            if http.script_wrap and http.script_wrap.script:
                if http.script_wrap.lang == ScriptType.PYTHON.value:
                    script_lang = " python"
                else:
                    script_lang = ""
                if http.script_wrap.script.startswith("> {%"):
                    script_syntax  = http.script_wrap.script
                else:
                    script_syntax = "> {%" + new_line * 2 + http.script_wrap.script + new_line * 2 + "%}"
                output_str += new_line * 2 + script_syntax + script_lang + new_line * 3
            else:
                output_str += new_line * 3
            return output_str

    @staticmethod
    def apply_httpbook(model: Allhttp):
        arr = []
        for http in model.allhttps:
            arr.append({
                "kind": 2,
                "language": "dothttp-vscode",
                "value": HttpFileFormatter.format_http(http),
                "outputs": []
            })
        return json.dumps(arr)

    @staticmethod
    def apply_http(model: Allhttp):
        output_str = ""
        for http in model.allhttps:
            output_str = output_str + HttpFileFormatter.format_http(http)
        return output_str

    @staticmethod
    def format(model: Allhttp, filetype=HttpFileType.Httpfile):
        if filetype == HttpFileType.Httpfile:
            return HttpFileFormatter.apply_http(model)
        return HttpFileFormatter.apply_httpbook(model)

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
        self.load_def()
        execution_cls = js3py.ScriptExecutionJs  if self.httpdef.test_script_lang == ScriptType.JAVA_SCRIPT  else js3py.ScriptExecutionPython
        script_execution = execution_cls(self.httpdef, self.property_util)
        script_execution.pre_request_script()
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
        self.write_to_output(resp)
        request_logger.debug(f'request executed completely')
        script_result = script_execution.execute_test_script(resp=resp)
        self.print_script_result(script_result)
        return resp

    def print_script_result(self, script_result: ScriptResult):
        print("\n------------")
        if script_result.stdout:
            print("\n##STDOUT:")
            print(script_result.stdout)
        if script_result.error:
            print("\n##ERROR:")
            print(script_result.error)
        if len(script_result.properties) != 0:
            print("\n##PROPERTIES:")
            pprint(script_result.properties)
        if len(script_result.tests) > 0:
            print("\n##TESTS:\n")
            for test in script_result.tests:
                print(f"Test: {test.name}  {'success' if test.success else 'failure!!'}")
                if test.result:
                    print(f"result={test.result}")
                if test.error:
                    print(f"{test.error}")
        print("\n------------")
        # TODO print tests output individually
        request_logger.debug(f'script execution result {script_result}')

    def write_to_output(self, resp):
        output = self.get_output()
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

    def get_response(self):
        session = self.get_session()
        request = self.get_request()
        session.cookies = request._cookies
        if self.httpdef.p12:
            session.mount(request.url,
                          Pkcs12Adapter(pkcs12_filename=self.httpdef.p12[0],
                                        pkcs12_password=self.httpdef.p12[1]))
        try:
            resp: Response = session.send(request, cert=self.httpdef.certificate,
                                          verify=not self.httpdef.allow_insecure,
                                          # stream=True
                                          )
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
            try:
                session.cookies.save()  # lwpCookie has .save method
            except:
                pass
        if self.httpdef.session_clear:
            session.close()
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
