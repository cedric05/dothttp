from dataclasses import dataclass, field
from io import IOBase
from typing import BinaryIO, Dict, List, Optional, Tuple, Union
from urllib.parse import urlencode

from requests import PreparedRequest
from requests.auth import AuthBase, HTTPBasicAuth, HTTPDigestAuth

from ..utils.common import APPLICATION_JSON, json_to_urlencoded_array
from ..utils.constants import *
from .parse_models import Payload as ParsePayload
from .parse_models import *


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
    target: str = field(default_factory=lambda: "1")
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
        List[
            Union[
                Tuple[str, Tuple[str, BinaryIO, Optional[str]]],
                Tuple[str, Tuple[None, str, None]],
            ]
        ]
    ] = None

    def set_data(self, data):
        self.data = data

    def set_json_data(self, json_data):
        self.json = json_data

    def set_files(self, json_files):
        self.files = json_files

    def set_content_type(self, content_type):
        self.header = content_type

    def set_file_payload(self, file_name):
        self.filename = file_name


@dataclass
class Property:
    text: List = field(default_factory=list())
    key: Union[str, None] = None
    value: Union[str, None] = None


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
    no_parent_script = False
    test_script: str = ""
    test_script_lang: ScriptType = ScriptType.JAVA_SCRIPT
    proxy: Optional[Dict[str, str]] = None

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
                self.headers[BASEIC_AUTHORIZATION_HEADER] = request.headers.get(
                    BASEIC_AUTHORIZATION_HEADER
                )
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
        request_logger.debug(f"request prepared completely {prep}")
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
                    except BaseException:
                        return_data["text"] = "file conversion to uft-8 ran into error"
                    finally:
                        payload.data.close()
        elif payload.json:
            return_data["mimeType"] = APPLICATION_JSON
            return_data["text"] = json.dumps(payload.json)
        elif payload.files:
            return_data["mimeType"] = MULTIPART_FORM_INPUT
            params = []
            for name, (
                multipart_filename,
                multipart_content,
                mimetype,
            ) in payload.files:
                content = multipart_content
                if isinstance(content, IOBase):
                    multipart_filename = multipart_content.name
                    content = None
                params.append(
                    {
                        "name": name,
                        "fileName": multipart_filename,
                        "value": content,
                        "contentType": mimetype,
                    }
                )
            return_data["params"] = params
        return return_data

    def get_query(self):
        return (
            [
                {"name": key, "value": value}
                for key, values in self.query.items()
                for value in values
            ]
            if self.query
            else []
        )

    def get_headers(self):
        return (
            [{"name": key, "value": value} for key, value in self.headers.items()]
            if self.headers
            else []
        )

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
                        MultiPartFile(
                            name=filekey,
                            path=(
                                multipartdata[1].name
                                if multipartdata[0]
                                else multipartdata[1]
                            ),
                            type=multipartdata[2] if len(multipartdata) > 2 else None,
                        )
                    )

            payload = ParsePayload(
                data=data,
                datajson=datajson,
                file=file,
                json=json_payload,
                fileswrap=fileswrap,
                type=type,
            )

        query_lines = []
        if self.query:
            for key, values in self.query.items():
                for value in values:
                    query_lines.append(
                        Line(header=None, query=Query(key=key, value=value))
                    )
        auth_wrap = None
        if self.auth:
            if isinstance(self.auth, HTTPBasicAuth):
                auth_wrap = AuthWrap(
                    basic_auth=BasicAuth(self.auth.username, self.auth.password)
                )
            elif isinstance(self.auth, HTTPDigestAuth):
                auth_wrap = AuthWrap(
                    digest_auth=DigestAuth(self.auth.username, self.auth.password)
                )
            elif isinstance(self.auth, HttpNtlmAuth):
                auth_wrap = AuthWrap(
                    ntlm_auth=NtlmAuthWrap(self.auth.username, self.auth.password)
                )
            elif RequestsHawkAuth and isinstance(self.auth, RequestsHawkAuth):
                hawk_id = self.auth.credentials["id"]
                hawk_key = self.auth.credentials["key"]
                hawk_algorithm = self.auth.credentials["algorithm"]
                auth_wrap = AuthWrap(
                    hawk_auth=HawkAuth(hawk_id, hawk_key, hawk_algorithm)
                )
            elif isinstance(self.auth, AWS4Auth):
                aws_auth: AWS4Auth = self.auth
                auth_wrap = AuthWrap(
                    aws_auth=AwsAuthWrap(
                        aws_auth.access_id,
                        aws_auth.signing_key.secret_key,
                        aws_auth.service,
                        aws_auth.region,
                        aws_auth.session_token
                    )
                )
            elif isinstance(self.auth, AzureAuth):
                auth_wrap = AuthWrap(azure_auth=self.auth.azure_auth_wrap)
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
                header_lines.append(
                    Line(header=Header(key=key, value=value), query=None)
                )
        test_script = TestScript(self.test_script)
        test_script.lang = self.test_script_lang
        return Http(
            namewrap=NameWrap(self.name),
            extra_args=extra_args,
            urlwrap=UrlWrap(url=self.url, method=self.method),
            lines=header_lines + query_lines,
            payload=payload,
            certificate=certificate,
            output=None,
            authwrap=auth_wrap,
            description=None,
            script_wrap=test_script,
        )
