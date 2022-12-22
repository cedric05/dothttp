import logging
import mimetypes
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from io import IOBase
from typing import Union, List, Optional, Dict, DefaultDict, Tuple, BinaryIO, Any
from urllib.parse import urlencode, urljoin, uses_relative, uses_netloc, uses_params, uses_query, uses_fragment, \
    urlparse

from requests import PreparedRequest
from requests.auth import HTTPBasicAuth, HTTPDigestAuth, AuthBase
from requests.structures import CaseInsensitiveDict
from requests_hawk import HawkAuth as RequestsHawkAuth 

from .utils import get_real_file_path, triple_or_double_tostring, APPLICATION_JSON, json_to_urlencoded_array

try:
    from requests_aws4auth import AWS4Auth
except ImportError:
    AWS4Auth = None
try:
    from requests_ntlm import HttpNtlmAuth
except ImportError:
    HttpNtlmAuth = None

try:
    import jstyleson as json
    from jsonschema import validate
except ImportError:
    import json
    validate = None

from textx import TextXSyntaxError, metamodel_from_file

from .dsl_jsonparser import json_or_array_to_json
from .exceptions import *
from .parse_models import Allhttp, AuthWrap, DigestAuth, BasicAuth, Line, NtlmAuthWrap, Query, Http, NameWrap, UrlWrap, Header, \
    MultiPartFile, FilesWrap, TripleOrDouble, Payload as ParsePayload, Certificate, P12Certificate, ExtraArg, \
    AWS_REGION_LIST, AWS_SERVICES_LIST, AwsAuthWrap, TestScript, ScriptType, HawkAuth
from .property_schema import property_schema
from .property_util import PropertyProvider

try:
    import magic
except ImportError:
    magic = None

base_logger = logging.getLogger("dothttp")
request_logger = logging.getLogger("request")
curl_logger = logging.getLogger("curl")

MIME_TYPE_JSON = "application/json"
FORM_URLENCODED = "application/x-www-form-urlencoded"
MULTIPART_FORM_INPUT = "multipart/form-data"
TEXT_PLAIN = "text/plain"

CONTENT_TYPE = 'content-type'

UNIX_SOCKET_SCHEME = "http+unix"

BASEIC_AUTHORIZATION_HEADER = "Authorization"


def install_unix_socket_scheme():
    uses_relative.append(UNIX_SOCKET_SCHEME)
    uses_netloc.append(UNIX_SOCKET_SCHEME)
    uses_params.append(UNIX_SOCKET_SCHEME)
    uses_query.append(UNIX_SOCKET_SCHEME)
    uses_fragment.append(UNIX_SOCKET_SCHEME)


install_unix_socket_scheme()

dothttp_model = metamodel_from_file(get_real_file_path(path="http.tx", current_file=__file__))


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
    content: str = None


@dataclass
class Payload:
    data: Optional[Union[str, bytes, Dict, BinaryIO]] = None
    json: Optional[Dict] = None
    header: Optional[str] = None
    filename: str = None
    # [[ "key", ["filename", "content", "datatype"],
    #  ["key",  ["filename2", "content", "datatype"]],
    #  ["key2",  [None, "content", "datatype"]],]
    files: Optional[
        List[Union[Tuple[str, Tuple[str, BinaryIO, Optional[str]]], Tuple[str, Tuple[None, str, None]]]]] = None


@dataclass
class HttpDef:
    name: str = None
    method: str = None
    url: str = None
    headers: dict = None
    query: dict = None
    auth: AuthBase = None
    payload: Optional[Payload] = None
    certificate: Optional[List[str]] = None
    p12: Optional[List[str]] = None
    output: str = None
    allow_insecure = False
    session_clear = False
    test_script: str = ""
    test_script_lang: ScriptType = ScriptType.JAVA_SCRIPT

    def get_har(self):
        if self.auth:
            request = self.get_prepared_request()
            # till now url and headers are enough
            # in future according that,
            # include all params
            # not giving inaccurate results
            self.auth(request)
            # For any other auth, it is bad
            if isinstance(self.auth, HTTPBasicAuth):
                self.headers[BASEIC_AUTHORIZATION_HEADER] = request.headers.get(BASEIC_AUTHORIZATION_HEADER)
            elif isinstance(self.auth, AWS4Auth):
                for header_key, header_value in request.headers.items():
                    self.headers[header_key] = header_value
            # # har with httpdigest is not possible
            # # as auth is set once, request is redirected to 401
            # # for now, ignoring
            # # also for har, certificate also has to be ignored
            # # har does't support this
            # # --------------------------
            # elif isinstance(self.auth, HTTPDigestAuth):
            #     self.headers[BASEIC_AUTHORIZATION_HEADER] = self.auth.build_digest_header(self.method, self.url)

        target = {
            "url": self.url,
            "method": self.method,
            "query": self.get_query(),
            "headers": self.get_headers(),
            "payload": self.get_payload(),
        }
        return target

    def get_prepared_request(self):
        prep = PreparedRequest()
        prep.prepare_url(self.url, self.query)
        prep.prepare_method(self.method)
        prep.prepare_headers(self.headers)
        payload = self.payload
        prep.prepare_body(data=payload.data, json=payload.json, files=payload.files)
        prep.prepare_auth(self.auth, self.url)
        request_logger.info(f"auth configured is {self.auth}")
        # prep.prepare_hooks({"response": self.save_cookie_call_back})
        if payload.header and CONTENT_TYPE not in prep.headers:
            # if content-type is provided by header
            # we will not wish to update it
            prep.headers[CONTENT_TYPE] = payload.header
        request_logger.debug(f'request prepared completely {prep}')
        return prep

    def get_payload(self):
        if not self.payload:
            return None
        payload = self.payload
        return_data = {}
        if payload.data:
            if isinstance(payload.data, dict):
                return_data["mimeType"] = FORM_URLENCODED
                return_data["text"] = urlencode(json_to_urlencoded_array(payload.data))
            else:
                return_data["mimeType"] = payload.header or "text/plain"
                if isinstance(payload.data, (str, bytes)):
                    return_data["text"] = payload.data
                else:
                    try:
                        data_read = payload.data.read()
                        return_data["text"] = data_read.decode("utf-8")
                    except:
                        return_data["text"] = "file conversion to uft-8 ran into error"
                    finally:
                        payload.data.close()
        elif payload.json:
            return_data["mimeType"] = APPLICATION_JSON
            return_data["text"] = json.dumps(payload.json)
        elif payload.files:
            return_data["mimeType"] = MULTIPART_FORM_INPUT
            params = []
            for (name, (multipart_filename, multipart_content, mimetype)) in payload.files:
                content = multipart_content
                if isinstance(content, IOBase):
                    multipart_filename = multipart_content.name
                    content = None
                params.append({
                    "name": name,
                    "fileName": multipart_filename,
                    "value": content,
                    "contentType": mimetype
                })
            return_data["params"] = params
        return return_data

    def get_query(self):
        return [{"name": key, "value": value} for key, values in self.query.items() for value in
                values] if self.query else []

    def get_headers(self):
        return [{"name": key, "value": value} for key, value in self.headers.items()] if self.headers else []

    def get_http_from_req(self):
        data = None
        datajson = None
        file = None
        json_payload = None
        fileswrap = None
        type = None
        payload = None
        if self.payload:
            if self.payload.filename:
                file = self.payload.filename
            elif isinstance(self.payload.data, str):
                data = [TripleOrDouble(str=self.payload.data)]
            elif isinstance(self.payload.data, dict):
                datajson = self.payload.data
            elif self.payload.json:
                json_payload = self.payload.json
            elif self.payload.files:
                fileswrap = FilesWrap([])
                for filekey, multipartdata in self.payload.files:
                    fileswrap.files.append(
                        MultiPartFile(name=filekey,
                                      path=multipartdata[1].name if multipartdata[0] else multipartdata[1],
                                      type=multipartdata[2] if len(multipartdata) > 2 else None)
                    )

            payload = ParsePayload(data=data, datajson=datajson, file=file, json=json_payload, fileswrap=fileswrap,
                                   type=type)

        query_lines = []
        if self.query:
            for key, values in self.query.items():
                for value in values:
                    query_lines.append(Line(header=None, query=Query(key=key, value=value)))
        auth_wrap = None
        if self.auth:
            if isinstance(self.auth, HTTPBasicAuth):
                auth_wrap = AuthWrap(basic_auth=BasicAuth(self.auth.username, self.auth.password))
            elif isinstance(self.auth, HTTPDigestAuth):
                auth_wrap = AuthWrap(digest_auth=DigestAuth(self.auth.username, self.auth.password))
            elif isinstance(self.auth, HttpNtlmAuth):
                auth_wrap = AuthWrap(ntlm_auth=NtlmAuthWrap(self.auth.username, self.auth.password))
            elif isinstance(self.auth, RequestsHawkAuth):
                hawk_id = self.auth.credentials['id']
                hawk_key = self.auth.credentials['key']
                hawk_algorithm = self.auth.credentials['algorithm']
                auth_wrap = AuthWrap(hawk_auth=HawkAuth(hawk_id, hawk_key, hawk_algorithm))
            elif isinstance(self.auth, AWS4Auth):
                aws_auth: AWS4Auth = self.auth
                auth_wrap = AuthWrap(
                    aws_auth=AwsAuthWrap(aws_auth.access_id, aws_auth.signing_key.secret_key, aws_auth.service,
                                         aws_auth.region))
        certificate = None
        if self.certificate:
            certificate = Certificate(*self.certificate)
        elif self.p12:
            certificate = P12Certificate(*self.p12)
        extra_args = []
        if self.session_clear:
            extra_args.append(ExtraArg(clear="@clear"))
        if self.allow_insecure:
            extra_args.append(ExtraArg(insecure="@insecure"))
        header_lines = []
        if self.headers:
            for key, value in self.headers.items():
                header_lines.append(Line(header=Header(key=key, value=value), query=None))
        test_script = TestScript(self.test_script)
        test_script.lang = self.test_script_lang
        return Http(
            namewrap=NameWrap(self.name),
            extra_args=extra_args,
            urlwrap=UrlWrap(url=self.url, method=self.method),
            lines=header_lines + query_lines,
            payload=payload,
            certificate=certificate,
            output=None, authwrap=auth_wrap, description=None, script_wrap=test_script
        )


@dataclass
class Property:
    text: List = field(default_factory=list())
    key: Union[str, None] = None
    value: Union[str, None] = None


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
        if not self.property_file and self.file:
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
                    if validate:
                        validate(instance=props, schema=property_schema)
                except Exception as e:
                    base_logger.error(f'property json schema validation failed! ', exc_info=True)
                    raise PropertyFileException(message="property file has invalid json schema",
                                                file=self.property_file)

        else:
            props = {}
        self.default_headers.update(props.get('headers', {}))
        self.property_util.add_env_property_from_dict(props.get("*", {}))
        if self.env:
            for env_name in self.env:
                self.property_util.add_env_property_from_dict(props.get(env_name, {}))

    def __init__(self, args: Config):
        self.args = args
        self.file = args.file
        # dev can define default headers, which dev dont want to do it for all requests
        # in most scenarios, headers are either computed or common across all other requests
        # best syntax would be headers section of property file will define default headers
        self.default_headers = {}
        self.property_file = args.property_file
        self.env = args.env
        self.content = ''
        self.original_content = self.content = ''
        self.property_util = PropertyProvider(self.property_file)
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
                index = prop.find("=")
                if index == -1:
                    raise
                key = prop[:index]
                value = prop[index + 1:]
                base_logger.debug(f"detected command line property {key} value: {value}")
                self.property_util.add_command_property(key, value)
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
        with open(self.file, 'r', encoding="utf-8") as f:
            self.original_content = self.content = f.read()

    def get_updated_content(self, content) -> str:
        return self.property_util.get_updated_content(content)

    def get_updated_content_object(self, content) -> str:
        return self.property_util.get_updated_content(content, 'obj')

    def select_target(self):
        if target := self.args.target:
            self.http = self.get_target(target, self.model.allhttps)
        else:
            self.http = self.model.allhttps[0]
        self.base_http = None
        if self.http.namewrap and self.http.namewrap.base:
            base = self.http.namewrap.base
            if base == self.http.namewrap.name:
                raise ParameterException(message="target and base should not be equal", key=target,
                                         value=base)
            try:
                self.base_http = self.get_target(base, self.model.allhttps)
            except Exception:
                raise UndefinedHttpToExtend(target=self.http.namewrap.name, base=base)

    @staticmethod
    def get_target(target: Union[str, int], http_def_list: List[Http]):
        if not isinstance(target, str):
            target = str(target)
        if target.isdecimal():
            if 1 <= int(target) <= len(http_def_list):
                selected = http_def_list[int(target) - 1]
            else:
                raise ParameterException(message="target startswith 1", key='target',
                                         value=target)
        else:
            try:
                # if multiple names have same value, it will create confusion
                # if they want to go with that. then pass id
                selected = next(filter(lambda http: http.namewrap.name == target,
                                       (http for http in http_def_list if http.namewrap)))
            except StopIteration:
                raise ParameterException(message="target is not spelled correctly", key='target',
                                         value=target)
        return selected

    def validate_names(self):
        names = []
        for index, http in enumerate(self.model.allhttps):
            name = http.namewrap.name if http.namewrap else str(index + 1)
            if name in names:
                raise HttpFileException(message=f"target: `{name}` appeared twice or more. panicked while processing")
            names.append(name)
            names.append(str(index + 1))

    def load_props_needed_for_content(self):
        self.property_util.add_infile_properties(self.content)


class HttpDefBase(BaseModelProcessor):
    def __init__(self, args: Config):
        super().__init__(args)
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

    def remove_quotes(self, header, s="'"):
        if header.key.startswith(s) and header.value.endswith(s):
            header.key = header.key[1:]
            header.value = header.value[:-1]

    def load_headers(self):
        """
            entrypoints
                1. dev defines headers in http file
                2. dev defines headers in property file
                3. dev defines headers via basic auth (only for Authorization)
                4. dev can define in data/file/files's type attribute section for ('content-type')
        :return:
        """
        ## headers are case insensitive
        ## having duplicate headers creates problem while exporting to curl,postman import..
        headers = CaseInsensitiveDict()
        headers.update(self.default_headers)
        self.load_headers_to_dict(self.base_http, headers)
        self.load_headers_to_dict(self.http, headers)
        request_logger.debug(
            f'computed query params from `{self.file}` are `{headers}`')
        self.httpdef.headers = headers

    def load_headers_to_dict(self, http, headers):
        if not http:
            return
        for line in http.lines:
            if header := line.header:
                self.remove_quotes(header, "'")
                self.remove_quotes(header, '"')
                headers[self.get_updated_content(header.key)] = self.get_updated_content(header.value)

    def load_certificate(self):
        request_logger.debug(
            f'url is {self.http.certificate}')
        certificate: Union[Certificate, P12Certificate] = self.get_current_or_base("certificate")
        if certificate:
            if certificate.cert:
                self.httpdef.certificate = [self.get_updated_content(certificate.cert),
                                            self.get_updated_content(certificate.key) if certificate.key else None]
            elif certificate.p12_file:
                self.httpdef.p12 = [self.get_updated_content(certificate.p12_file),
                                    self.get_updated_content(certificate.password)]

    def load_extra_flags(self):
        # flags are extendable
        # once its marked as allow insecure
        # user would want all child to have same effect
        extra_args = self.http.extra_args
        if self.base_http and self.base_http.extra_args:
            extra_args += self.base_http.extra_args
        if extra_args:
            for flag in extra_args:
                if flag.clear:
                    self.httpdef.session_clear = True
                elif flag.insecure:
                    self.httpdef.allow_insecure = True

    def load_url(self):
        request_logger.debug(
            f'url is {self.http.urlwrap.url}')
        url_path = self.get_updated_content(self.http.urlwrap.url)
        if base_http := self.base_http:
            base_url = self.get_updated_content(base_http.urlwrap.url)
            if not url_path:
                self.httpdef.url = base_url
            elif url_path.startswith("http://") or url_path.startswith("https://") or url_path.startswith(
                    "http+unix://"):
                self.httpdef.url = url_path
            elif base_url.endswith("/") and url_path.startswith("/"):
                self.httpdef.url = urljoin(base_url, url_path[1:])
            elif url_path.startswith("/"):
                self.httpdef.url = urljoin(base_url + "/", url_path[1:])
            elif not base_url.endswith("/") and not url_path.startswith("/"):
                self.httpdef.url = urljoin(base_url + "/", url_path)
            else:
                self.httpdef.url = urljoin(base_url, url_path)
        else:
            self.httpdef.url = url_path
        if self.httpdef.url and not (
                self.httpdef.url.startswith("https://")
                or
                self.httpdef.url.startswith("http://")
                or
                self.httpdef.url.startswith("http+unix://")

        ):
            self.httpdef.url = "http://" + self.httpdef.url

    def load_method(self):
        if method := self.http.urlwrap.method:
            request_logger.debug(
                f'method defined in `{self.file}` is {method}')
            self.httpdef.method = method
            return
        request_logger.debug(
            f'method not defined in `{self.file}`. defaults to `GET`')
        if self.http.payload:
            self.httpdef.method = "POST"
        else:
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
        elif self.http.payload.data:
            content = triple_or_double_tostring(self.http.payload.data, self.get_updated_content)
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
            return self.load_payload_fileinput(upload_filename)
        elif json_data := self.http.payload.json:
            d = json_or_array_to_json(json_data, self.get_updated_content)
            return Payload(json=d, header=MIME_TYPE_JSON)
        elif files_wrap := self.http.payload.fileswrap:
            files = []
            for multipart_file in files_wrap.files:
                if multipart_file.path.triple:
                    multipart_file_path = multipart_file.path.triple[3:-3]
                else:
                    multipart_file_path = multipart_file.path.str
                multipart_content = self.get_updated_content(multipart_file_path)
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
            return Payload(files=files, header=MULTIPART_FORM_INPUT)
        return Payload()

    def load_payload_fileinput(self, upload_filename):
        upload_filename = self.get_updated_content(upload_filename)
        request_logger.debug(
            f'payload will be loaded from `{upload_filename}`')
        if not os.path.exists(upload_filename):
            request_logger.debug(
                f'payload file `{upload_filename}` Not found. ')
            raise DataFileNotFoundException(datafile=upload_filename)
        mimetype = self.get_mimetype_from_file(upload_filename, self.http.payload.type)
        f = open(upload_filename, 'rb')
        return Payload(data=f, header=mimetype, filename=upload_filename)

    @staticmethod
    def get_mimetype_from_file(filename, mimetype: Optional[str]) -> Optional[str]:
        if mimetype:
            return mimetype
        if magic:
            mimetype = magic.from_file(filename, mime=True)
        elif mimetypes:
            mimetype = mimetypes.guess_type(filename, strict=False)[0]
        return mimetype

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
            request_logger.warning(f'output will be written to `{os.path.abspath(output_file)}`')
            request_logger.debug(
                f'output will be written into `{self.file}` is `{os.path.abspath(output_file)}`')
            try:
                return open(output_file, 'wb')
            except Exception as e:
                request_logger.debug(
                    f'not able to open `{output}`. output will be written to stdout', exc_info=True)
                raise
        else:
            return sys.stdout

    def load_auth(self):
        auth_wrap:AuthWrap = self.get_current_or_base("authwrap")
        if auth_wrap:
            if basic_auth := auth_wrap.basic_auth:
                self.httpdef.auth = HTTPBasicAuth(self.get_updated_content(basic_auth.username),
                                                  self.get_updated_content(
                                                      basic_auth.password))
            elif digest_auth := auth_wrap.digest_auth:
                self.httpdef.auth = HTTPDigestAuth(self.get_updated_content(digest_auth.username),
                                                   self.get_updated_content(
                                                       digest_auth.password))
            elif ntlm_auth := auth_wrap.ntlm_auth:
                self.httpdef.auth = HttpNtlmAuth(self.get_updated_content(ntlm_auth.username), 
                                                 self.get_updated_content(ntlm_auth.password))
            elif hawk_auth := auth_wrap.hawk_auth:
                if hawk_auth.algorithm:
                    algorithm = hawk_auth.algorithm
                else:
                    algorithm = "sha256"
                self.httpdef.auth =  RequestsHawkAuth(
                                        id=self.get_updated_content(hawk_auth.id), 
                                        key=self.get_updated_content(hawk_auth.key),
                                        algorithm=self.get_updated_content(algorithm))
            elif aws_auth_wrap := auth_wrap.aws_auth:
                access_id = self.get_updated_content(aws_auth_wrap.access_id)
                secret_token = self.get_updated_content(aws_auth_wrap.secret_token)
                aws_service = None
                aws_region = None
                if aws_auth_wrap.service:
                    aws_service = self.get_updated_content(aws_auth_wrap.service)
                if aws_auth_wrap.region:
                    aws_region = self.get_updated_content(aws_auth_wrap.region)
                parsed_url = urlparse(self.httpdef.url)
                hostname = parsed_url.hostname
                if hostname.endswith(".amazonaws.com"):
                    # s3.amazonaws.com
                    # ec2.amazonaws.com
                    hosts = hostname.split('.')
                    if len(hosts) == 3:
                        if aws_region is None:
                            # if region is not defined,
                            # us-east-1 is considered as region
                            aws_region = "us-east-1"
                            base_logger.warning(f"region not defined, so defaulting with {aws_region}")
                        if aws_service:
                            if (hosts[-3] in AWS_SERVICES_LIST and aws_service != hosts[-3]):
                                # host is in predefiend aws_service list
                                # and is not equals to given values
                                # which clearly indicates
                                # that user is mistaken
                                # we will currect it here
                                base_logger.warning(
                                    f"aws_service = {aws_service} and service from url is {hosts[0]}. incorrectly defined")
                                aws_service = hosts[-3]
                        else:
                            # user has not specified aws service
                            # we can check with predefiend aws_service_list but
                            # aws_service_list may not be complete.
                            # so we are blicdly going with user given url
                            aws_service = hosts[-3]
                        # aws also supports
                        # legacy https://s3-us-east-1.amazonaws.com
                        # https://ec2-us-east-1.amazonaws.com
                        index = hosts[-3].find('-')
                        if index != -1:
                            base_logger.info("figuring out service and region host via legacy")
                            _aws_service = hosts[-3][:index]
                            _aws_region = hosts[-3][index + 1:]
                            # aws_region is not figured till now
                            # according to above definition
                            # we can consider aws_region and aws_service like below
                            if (not aws_region) or (_aws_region in AWS_REGION_LIST and aws_region != _aws_region):
                                aws_region = _aws_region
                            if (not aws_service) or (_aws_service in AWS_SERVICES_LIST and aws_service != _aws_service):
                                aws_service = _aws_service
                    elif len(hosts) >= 4:
                        if hosts[-4] in AWS_SERVICES_LIST:
                            if aws_service:
                                if hosts[-4] != aws_service:
                                    base_logger.warning(
                                        f"aws_service = {aws_service} and service from url is {hosts[0]}. incorrectly defined")
                                    aws_service = hosts[-4]
                            else:
                                # user has not provided service
                                # from url, service can be deduced
                                aws_service = hosts[-4]
                            base_logger.info(f"default with url service defined in url (`{aws_service}`)")
                        if hosts[-3] in AWS_REGION_LIST:
                            # host is in predefined region list
                            if aws_region:
                                if hosts[-3] != aws_region:
                                    base_logger.warning(
                                        f"aws_service = {aws_region} and service from url is {hosts[1]}. incorrectly defined")
                                    aws_region = hosts[-3]
                                    base_logger.info(f"default with url service defined in url (`{aws_region}`)")
                            else:
                                # user has not provided service
                                # from url, service can be deduced
                                aws_region = hosts[-3]
                if not aws_region:
                    aws_region = 'us-east-1'
                if access_id and secret_token and aws_service and aws_region:
                    base_logger.info(f"aws request with region aws_service: {aws_service} region: {aws_region}")
                    self.httpdef.auth = AWS4Auth(
                        access_id,
                        secret_token,
                        aws_region,
                        aws_service
                    )
                else:
                    ## region and aws_service can be extracted from url
                    ## somehow library is not supporting those
                    ## with current state, we are not support this use case
                    ## we may come back
                    ## all four parameters are required and are to be non empty
                    raise DothttpAwsAuthException(access_id = access_id)

    def get_current_or_base(self, attr_key) -> Any:
        if getattr(self.http, attr_key):
            return getattr(self.http, attr_key)
        elif self.base_http:
            return getattr(self.base_http, attr_key)

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
        self.load_certificate()
        self.load_test_script()
        self.load_extra_flags()
        self.load_output()
        self._loaded = True

    def load_test_script(self):
        self.httpdef.test_script = ""
        script_wrap: TestScript = self.get_current_or_base("script_wrap")
        if script_wrap and script_wrap.script:
            script = script_wrap.script[4:-2]
            self.httpdef.test_script = script.strip()
            self.httpdef.test_script_lang = ScriptType.get_script_type(script_type=script_wrap.lang)

    def load_output(self):
        if self.http.output and self.http.output.output:
            self.httpdef.output = self.http.output.output
