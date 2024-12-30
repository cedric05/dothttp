import mimetypes
import os
import re
import sys
from collections import defaultdict
from functools import lru_cache
from typing import Any, DefaultDict, Dict, List, Optional, Union
from urllib.parse import (
    urljoin,
    urlparse,
    uses_fragment,
    uses_netloc,
    uses_params,
    uses_query,
    uses_relative,
)

import toml
import yaml
from requests.auth import HTTPBasicAuth, HTTPDigestAuth
from requests.structures import CaseInsensitiveDict
from textx import TextXSyntaxError, metamodel_from_file

from ..exceptions import *
from ..models.computed import *
from ..models.parse_models import (
    AWS_REGION_LIST,
    AWS_SERVICES_LIST,
    AuthWrap,
    AzureAuthCertificate,
    AzureAuthCli,
    AzureAuthDeviceCode,
    AzureAuthServicePrincipal,
    AzureAuthType,
    AzureAuthWrap,
    Certificate,
    Http,
    MultidefHttp,
    P12Certificate,
    ScriptType,
    TestScript,
)
from ..property_schema import property_schema
from ..script import ScriptExecutionJs, ScriptExecutionPython
from ..utils.common import get_real_file_path, triple_or_double_tostring
from ..utils.constants import *
from ..utils.property_util import PropertyProvider
from .dsl_jsonparser import json_or_array_to_json, jsonmodel_to_json


def install_unix_socket_scheme():
    uses_relative.append(UNIX_SOCKET_SCHEME)
    uses_netloc.append(UNIX_SOCKET_SCHEME)
    uses_params.append(UNIX_SOCKET_SCHEME)
    uses_query.append(UNIX_SOCKET_SCHEME)
    uses_fragment.append(UNIX_SOCKET_SCHEME)


install_unix_socket_scheme()

dothttp_model = metamodel_from_file(
    get_real_file_path(path="../http.tx", current_file=__file__)
)


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


class BaseModelProcessor:
    var_regex = re.compile(r"{{(?P<var>.*?)}}")

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
            base_logger.debug("property file not specified")
            default_json = os.path.join(os.path.dirname(self.file), ".dothttp.json")
            default_yaml = os.path.join(os.path.dirname(self.file), ".dothttp.yaml")
            default_yml = os.path.join(os.path.dirname(self.file), ".dothttp.yml")
            default_toml = os.path.join(os.path.dirname(self.file), ".dothttp.toml")
            if os.path.exists(default_json):
                base_logger.debug(
                    f"file: {default_json} exists. it will be used for property reference"
                )
                self.property_file = default_json
            elif os.path.exists(default_yaml):
                base_logger.debug(
                    f"file: {default_yaml} exists. it will be used for property reference"
                )
                self.property_file = default_yaml
            elif os.path.exists(default_yml):
                base_logger.debug(
                    f"file: {default_yaml} exists. it will be used for property reference"
                )
                self.property_file = default_yml
            elif os.path.exists(default_toml):
                base_logger.debug(
                    f"file: {default_yaml} exists. it will be used for property reference"
                )
                self.property_file = default_toml
        if self.property_file and not os.path.exists(self.property_file):
            base_logger.debug(f"file: {self.property_file} not found")
            raise PropertyFileNotFoundException(propertyfile=self.property_file)
        if self.property_file:
            with open(self.property_file, "r") as f:
                try:
                    if self.property_file.endswith(".json"):
                        props = json.load(f)
                    elif self.property_file.endswith(
                        ".yaml"
                    ) or self.property_file.endswith(".yml"):
                        props = yaml.load(f, yaml.SafeLoader)
                    elif self.property_file.endswith(".toml"):
                        props = toml.load(f)
                    else:
                        raise Exception("unrecognized property file")
                    base_logger.debug(f"file: {self.property_file} loaded successfully")
                except Exception as e:
                    base_logger.error(
                        f"exception loading property file ", exc_info=True
                    )
                    raise PropertyFileNotJsonException(propertyfile=self.property_file)
                try:
                    if validate:
                        validate(instance=props, schema=property_schema)
                except Exception as e:
                    base_logger.error(
                        f"property json schema validation failed! ", exc_info=True
                    )
                    raise PropertyFileException(
                        message="property file has invalid json schema",
                        file=self.property_file,
                    )

        else:
            props = {}
        self.default_headers.update(props.get("headers", {}))
        self.property_util.add_env_property_from_dict(props.get("*", {}))
        self.property_util.add_system_command_properties(props.get("$commands", {}))
        if self.env:
            for env_name in self.env:
                self.property_util.add_env_property_from_dict(props.get(env_name, {}))

    def __init__(self, args: Config):
        self.args = args
        self.file = args.file
        # dev can define default headers, which dev dont want to do it for all requests
        # in most scenarios, headers are either computed or common across all other requests
        # best syntax would be headers section of property file will define
        # default headers
        self.default_headers = {}
        self.property_file = args.property_file
        self.env = args.env
        self.content = ""
        self.original_content = self.content = ""
        self.property_util = PropertyProvider(self.property_file)
        self.load()

    def load(self):
        self.load_content()
        self.load_model()
        self.load_imports()
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
                value = prop[index + 1 :]
                base_logger.debug(
                    f"detected command line property {key} value: {value}"
                )
                self.property_util.add_command_line_property(key, value)
            except BaseException:
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
        self.model: MultidefHttp = model

    def load_imports(self):
        self._load_imports(
            self.model, self.file, self.property_util, self.model.allhttps
        )

    @staticmethod
    def _load_imports(
        model: "BaseModelProcessor",
        filename: str,
        property_util: PropertyProvider,
        import_list: [],
    ):
        for model, content in BaseModelProcessor._get_models_from_import(
            model, filename
        ):
            import_list += model.allhttps
            BaseModelProcessor.load_properties_from_var(model, property_util)
            property_util.add_infile_properties(content)

    @staticmethod
    def _get_models_from_import(model: MultidefHttp, filename: str):
        if not model.import_list:
            return
        for filename_string in model.import_list.filename:
            import_file = filename_string.value
            if not os.path.isabs(import_file):
                import_file = os.path.join(
                    os.path.dirname(os.path.realpath(filename)), import_file
                )
            if not os.path.isfile(import_file):
                if os.path.isfile(import_file + ".http"):
                    import_file += ".http"
                else:
                    raise HttpFileException(
                        message=f"import file should be a file, current: {import_file}"
                    )
            with open(import_file, "r", encoding="utf-8") as f:
                imported_content = f.read()
                try:
                    imported_model = dothttp_model.model_from_str(imported_content)
                    yield imported_model, imported_content
                except TextXSyntaxError as e:
                    raise HttpFileSyntaxException(file=import_file, message=e.args)
                except Exception as e:
                    raise HttpFileException(message=e.args)
            yield from BaseModelProcessor._get_models_from_import(
                imported_model, import_file
            )
        return

    def load_content(self):
        if not os.path.exists(self.file):
            raise HttpFileNotFoundException(file=self.file)
        with open(self.file, "r", encoding="utf-8") as f:
            self.original_content = self.content = f.read()

    def get_updated_content(self, content) -> str:
        return self.property_util.get_updated_content(content)

    def get_updated_content_object(self, content) -> str:
        return self.property_util.get_updated_content(content, "obj")

    def select_target(self):
        if target := self.args.target:
            self.http = self.get_target(target, self.model.allhttps)
        else:
            self.http = self.model.allhttps[0]
        self.parents_http = []
        if self.http.namewrap and self.http.namewrap.base:
            parent = self.http.namewrap.base
            if parent == self.http.namewrap.name:
                raise ParameterException(
                    message="target and base should not be equal",
                    key=target,
                    value=parent,
                )
            try:
                while parent:
                    if parent in self.parents_http:
                        raise ParameterException(
                            message="Found circular reference",
                            target=self.http.namewrap.name,
                        )
                    grand_http = self.get_target(parent, self.model.allhttps)
                    self.parents_http.append(grand_http)
                    parent = grand_http.namewrap.base
            except Exception:
                raise UndefinedHttpToExtend(target=self.http.namewrap.name, base=parent)

    @staticmethod
    def get_target(target: Union[str, int], http_def_list: List[Http]):
        if not isinstance(target, str):
            target = str(target)
        if target.isdecimal():
            if 1 <= int(target) <= len(http_def_list):
                selected = http_def_list[int(target) - 1]
            else:
                raise ParameterException(
                    message="target startswith 1", key="target", value=target
                )
        else:
            try:
                # if multiple names have same value, it will create confusion
                # if they want to go with that. then pass id
                selected = next(
                    filter(
                        lambda http: http.namewrap.name == target,
                        (http for http in http_def_list if http.namewrap),
                    )
                )
            except StopIteration:
                raise ParameterException(
                    message="target is not spelled correctly",
                    key="target",
                    value=target,
                )
        return selected

    def validate_names(self):
        names = []
        for index, http in enumerate(self.model.allhttps):
            name = http.namewrap.name if http.namewrap else str(index + 1)
            if name in names:
                raise HttpFileException(
                    message=f"target: `{name}` appeared twice or more. panicked while processing"
                )
            names.append(name)
            names.append(str(index + 1))

    def load_props_needed_for_content(self):
        self._load_props_from_content(self.content, self.property_util)

    def _load_props_from_content(self, content, property_util: PropertyProvider):
        self.load_properties_from_var(self.model, property_util)
        property_util.add_infile_properties(content)
    
    @staticmethod
    def load_properties_from_var(model:MultidefHttp, property_util: PropertyProvider):
        ## this has to taken care by property util
        ## but it will complicate the code
        for variable in model.variables:
            if variable.value:
                var_value = jsonmodel_to_json(variable.value)
                property_util.add_infile_property_from_var(variable.name, var_value)
            elif variable.func:
                func_name = f"${variable.func.name}"
                if func_name in property_util.rand_map:
                    func = property_util.rand_map[func_name]
                    if variable.func.args:
                        args = variable.func.args
                        var_value = func(args)
                    else:
                        var_value = func()
                else:
                    var_value = variable.func.name
                property_util.add_infile_property_from_var(variable.name, var_value)
            elif variable.inter:
                class PropertyResolver:
                    # hassle of creating class is to make it work with format_map
                    # instead of format which can be used with dict and can cause memory leak
                    def __getitem__(self, key):
                        if key in property_util.command_line_properties:
                            return property_util.command_line_properties[key]
                        if key in property_util.env_properties:
                            return property_util.env_properties[key]
                        if key in property_util.infile_properties and property_util.infile_properties[key].value is not None:
                            return property_util.infile_properties[key].value
                        raise KeyError(key)
                var_value = variable.inter[2:-1].format_map(PropertyResolver())
                property_util.add_infile_property_from_var(variable.name, var_value)


class HttpDefBase(BaseModelProcessor):
    def __init__(self, args: Config):
        super().__init__(args)
        self.httpdef = HttpDef()
        self._loaded = False

    def load_query(self):
        params: DefaultDict[List] = defaultdict(list)
        for parent in self.parents_http:
            for line in parent.lines:
                if query := line.query:
                    params[self.get_updated_content(query.key)].append(
                        self.get_updated_content(query.value)
                    )
        for line in self.http.lines:
            if query := line.query:
                params[self.get_updated_content(query.key)].append(
                    self.get_updated_content(query.value)
                )
        request_logger.debug(f"computed query params from `{self.file}` are `{params}`")
        self.httpdef.query = params

    def remove_quotes(self, header, s="'"):
        if header.key.startswith(s) and header.value.endswith(s):
            header.key = header.key[1:]
            header.value = header.value[:-1]

    def load_proxy(self):
        proxy_dict = dict()
        for http_parent in self.parents_http:
            HttpDefBase._load_proxy_details(http_parent, proxy_dict, self.property_util)
        HttpDefBase._load_proxy_details(self.http, proxy_dict, self.property_util)
        self.httpdef.proxy = proxy_dict

    def _load_proxy_details(
        http: Http, property_util: PropertyProvider, proxy_dict: Dict[str, str]
    ):
        if http.named_args:
            for arg in http.named_args:
                if arg.key == "http.proxy":
                    proxy_dict["http"] = (
                        property_util.get_updated_content(arg.value)
                        if arg.value
                        else None
                    )
                elif arg.key == "https.proxy":
                    proxy_dict["https"] = (
                        property_util.get_updated_content(arg.value)
                        if arg.value
                        else None
                    )

    def load_headers(self):
        """
            entrypoints
                1. dev defines headers in http file
                2. dev defines headers in property file
                3. dev defines headers via basic auth (only for Authorization)
                4. dev can define in data/file/files's type attribute section for ('content-type')
        :return:
        """
        # headers are case insensitive
        # having duplicate headers creates problem while exporting to
        # curl,postman import..
        headers = CaseInsensitiveDict()
        headers.update(self.default_headers)
        for parent in self.parents_http:
            self.load_headers_to_dict(parent, headers)
        self.load_headers_to_dict(self.http, headers)
        request_logger.debug(
            f"computed query params from `{self.file}` are `{headers}`"
        )
        self.httpdef.headers = headers

    def load_headers_to_dict(self, http, headers):
        if not http:
            return
        for line in http.lines:
            if header := line.header:
                self.remove_quotes(header, "'")
                self.remove_quotes(header, '"')
                headers[
                    self.get_updated_content(header.key)
                ] = self.get_updated_content(header.value)

    def load_certificate(self):
        request_logger.debug(f"url is {self.http.certificate}")
        certificate: Union[Certificate, P12Certificate] = self.get_current_or_base(
            "certificate"
        )
        if certificate:
            if certificate.cert:
                self.httpdef.certificate = [
                    self.get_updated_content(certificate.cert),
                    (
                        self.get_updated_content(certificate.key)
                        if certificate.key
                        else None
                    ),
                ]
            elif certificate.p12_file:
                self.httpdef.p12 = [
                    self.get_updated_content(certificate.p12_file),
                    self.get_updated_content(certificate.password),
                ]

    def load_extra_flags(self):
        # flags are extendable
        # once its marked as allow insecure
        # user would want all child to have same effect
        extra_args = list(self.http.extra_args)
        if self.parents_http:
            for parent in self.parents_http:
                if parent.extra_args:
                    extra_args += parent.extra_args
        if extra_args:
            for flag in extra_args:
                if flag.clear:
                    self.httpdef.session_clear = True
                elif flag.insecure:
                    self.httpdef.allow_insecure = True

        for current_flag in self.http.extra_args:
            if current_flag.no_parent_script:
                self.httpdef.no_parent_script = True

    def load_url(self):
        request_logger.debug(f"url is {self.http.urlwrap.url}")
        url_path = self.get_updated_content(self.http.urlwrap.url)
        if self.parents_http:
            for base_http in self.parents_http:
                base_url = self.get_updated_content(base_http.urlwrap.url)
                if not url_path:
                    url = base_url
                elif (
                    url_path.startswith("http://")
                    or url_path.startswith("https://")
                    or url_path.startswith("http+unix://")
                ):
                    url = url_path
                elif base_url.endswith("/") and url_path.startswith("/"):
                    url = urljoin(base_url, url_path[1:])
                elif url_path.startswith("/"):
                    url = urljoin(base_url + "/", url_path[1:])
                elif not base_url.endswith("/") and not url_path.startswith("/"):
                    url = urljoin(base_url + "/", url_path)
                else:
                    url = urljoin(base_url, url_path)
                url_path = url
            self.httpdef.url = url_path
        else:
            self.httpdef.url = url_path
        if self.httpdef.url and not (
            self.httpdef.url.startswith("https://")
            or self.httpdef.url.startswith("http://")
            or self.httpdef.url.startswith("http+unix://")
        ):
            self.httpdef.url = "http://" + self.httpdef.url

    def load_method(self):
        if method := self.http.urlwrap.method:
            request_logger.debug(f"method defined in `{self.file}` is {method}")
            self.httpdef.method = method
            return
        request_logger.debug(f"method not defined in `{self.file}`. defaults to `GET`")
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
            content = triple_or_double_tostring(
                self.http.payload.data, self.get_updated_content
            )
            mimetype = self.get_mimetype_from_buffer(
                content, self.get_updated_content(self.http.payload.type)
            )
            request_logger.debug(f"payload for request is `{content}`")
            return Payload(content, header=mimetype)
        elif data_json := self.http.payload.datajson:
            d = json_or_array_to_json(data_json, self.property_util)
            if isinstance(d, list):
                raise PayloadDataNotValidException(
                    payload=f"data should be json/str, current: {d}"
                )
            # TODO convert all into string
            # varstring hanlding
            return Payload(data=d, header=FORM_URLENCODED)
        elif upload_filename := self.http.payload.file:
            return self.load_payload_fileinput(upload_filename)
        elif json_data := self.http.payload.json:
            d = json_or_array_to_json(json_data, self.property_util)
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
                mimetype = (
                    self.get_updated_content(multipart_file.type)
                    if multipart_file.type
                    else None
                )
                if os.path.exists(
                    multipart_content
                ):  # probably check valid path, then check for exists
                    mimetype = self.get_mimetype_from_file(multipart_content, mimetype)
                    multipart_filename = os.path.basename(multipart_content)
                    multipart_content = open(multipart_content, "rb")
                    files.append(
                        (
                            multipart_key,
                            (multipart_filename, multipart_content, mimetype),
                        )
                    )
                else:
                    mimetype = self.get_mimetype_from_buffer(
                        multipart_content, mimetype
                    )
                    files.append((multipart_key, (None, multipart_content, mimetype)))
            return Payload(files=files, header=MULTIPART_FORM_INPUT)
        return Payload()

    def load_payload_fileinput(self, upload_filename):
        upload_filename = self.get_updated_content(upload_filename)
        request_logger.debug(f"payload will be loaded from `{upload_filename}`")
        if not os.path.exists(upload_filename):
            request_logger.debug(f"payload file `{upload_filename}` Not found. ")
            raise DataFileNotFoundException(datafile=upload_filename)
        mimetype = self.get_mimetype_from_file(upload_filename, self.http.payload.type)
        f = open(upload_filename, "rb")
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
            request_logger.warning(
                f"output will be written to `{os.path.abspath(output_file)}`"
            )
            request_logger.debug(
                f"output will be written into `{self.file}` is `{os.path.abspath(output_file)}`"
            )
            try:
                return open(output_file, "wb")
            except Exception as e:
                request_logger.debug(
                    f"not able to open `{output}`. output will be written to stdout",
                    exc_info=True,
                )
                raise
        else:
            return sys.stdout

    def load_auth(self):
        auth_wrap: AuthWrap = self.get_current_or_base("authwrap")
        if auth_wrap:
            if basic_auth := auth_wrap.basic_auth:
                self.httpdef.auth = HTTPBasicAuth(
                    self.get_updated_content(basic_auth.username),
                    self.get_updated_content(basic_auth.password),
                )
            elif digest_auth := auth_wrap.digest_auth:
                self.httpdef.auth = HTTPDigestAuth(
                    self.get_updated_content(digest_auth.username),
                    self.get_updated_content(digest_auth.password),
                )
            elif ntlm_auth := auth_wrap.ntlm_auth:
                self.httpdef.auth = HttpNtlmAuth(
                    self.get_updated_content(ntlm_auth.username),
                    self.get_updated_content(ntlm_auth.password),
                )
            elif hawk_auth := auth_wrap.hawk_auth:
                if hawk_auth.algorithm:
                    algorithm = hawk_auth.algorithm
                else:
                    algorithm = "sha256"
                self.httpdef.auth = RequestsHawkAuth(
                    id=self.get_updated_content(hawk_auth.id),
                    key=self.get_updated_content(hawk_auth.key),
                    algorithm=self.get_updated_content(algorithm),
                )
            elif aws_auth_wrap := auth_wrap.aws_auth:
                access_id = self.get_updated_content(aws_auth_wrap.access_id)
                secret_token = self.get_updated_content(aws_auth_wrap.secret_token)
                session_token = None
                aws_service = None
                aws_region = None
                if aws_auth_wrap.service:
                    aws_service = self.get_updated_content(aws_auth_wrap.service)
                if aws_auth_wrap.region:
                    aws_region = self.get_updated_content(aws_auth_wrap.region)
                if aws_auth_wrap.session_token:
                    session_token = self.get_updated_content(aws_auth_wrap.session_token)
                parsed_url = urlparse(self.httpdef.url)
                hostname = parsed_url.hostname
                if hostname.endswith(".amazonaws.com"):
                    # s3.amazonaws.com
                    # ec2.amazonaws.com
                    hosts = hostname.split(".")
                    if len(hosts) == 3:
                        if aws_region is None:
                            # if region is not defined,
                            # us-east-1 is considered as region
                            aws_region = "us-east-1"
                            base_logger.warning(
                                f"region not defined, so defaulting with {aws_region}"
                            )
                        if aws_service:
                            if (
                                hosts[-3] in AWS_SERVICES_LIST
                                and aws_service != hosts[-3]
                            ):
                                # host is in predefiend aws_service list
                                # and is not equals to given values
                                # which clearly indicates
                                # that user is mistaken
                                # we will currect it here
                                base_logger.warning(
                                    f"aws_service = {aws_service} and service from url is {hosts[0]}. incorrectly defined"
                                )
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
                        index = hosts[-3].find("-")
                        if index != -1:
                            base_logger.info(
                                "figuring out service and region host via legacy"
                            )
                            _aws_service = hosts[-3][:index]
                            _aws_region = hosts[-3][index + 1 :]
                            # aws_region is not figured till now
                            # according to above definition
                            # we can consider aws_region and aws_service like
                            # below
                            if (not aws_region) or (
                                _aws_region in AWS_REGION_LIST
                                and aws_region != _aws_region
                            ):
                                aws_region = _aws_region
                            if (not aws_service) or (
                                _aws_service in AWS_SERVICES_LIST
                                and aws_service != _aws_service
                            ):
                                aws_service = _aws_service
                    elif len(hosts) >= 4:
                        if hosts[-4] in AWS_SERVICES_LIST:
                            if aws_service:
                                if hosts[-4] != aws_service:
                                    base_logger.warning(
                                        f"aws_service = {aws_service} and service from url is {hosts[0]}. incorrectly defined"
                                    )
                                    aws_service = hosts[-4]
                            else:
                                # user has not provided service
                                # from url, service can be deduced
                                aws_service = hosts[-4]
                            base_logger.info(
                                f"default with url service defined in url (`{aws_service}`)"
                            )
                        if hosts[-3] in AWS_REGION_LIST:
                            # host is in predefined region list
                            if aws_region:
                                if hosts[-3] != aws_region:
                                    base_logger.warning(
                                        f"aws_service = {aws_region} and service from url is {hosts[1]}. incorrectly defined"
                                    )
                                    aws_region = hosts[-3]
                                    base_logger.info(
                                        f"default with url service defined in url (`{aws_region}`)"
                                    )
                            else:
                                # user has not provided service
                                # from url, service can be deduced
                                aws_region = hosts[-3]
                if not aws_region:
                    aws_region = "us-east-1"
                if access_id and secret_token and aws_service and aws_region:
                    base_logger.info(
                        f"aws request with region aws_service: {aws_service} region: {aws_region}"
                    )
                    self.httpdef.auth = AWS4Auth(
                        access_id, secret_token, aws_region, aws_service, session_token = session_token
                    )
                else:
                    # aws service and region can be extracted from url
                    # somehow library is not supporting those
                    # with current state, we are not support this use case
                    # we may come back
                    # all four parameters are required and are to be non empty
                    raise DothttpAwsAuthException(access_id=access_id)
            elif azure_auth := auth_wrap.azure_auth:
                azure_auth: AzureAuthWrap = azure_auth
                if sp_auth := azure_auth.azure_spsecret_auth:
                    azure_auth_wrap = AzureAuthWrap(
                        azure_spsecret_auth=AzureAuthServicePrincipal(
                            tenant_id=self.get_updated_content(sp_auth.tenant_id),
                            client_id=self.get_updated_content(sp_auth.client_id),
                            client_secret=self.get_updated_content(
                                sp_auth.client_secret
                            ),
                            scope=self.get_updated_content(
                                sp_auth.scope or "https://management.azure.com/.default"
                            ),
                        ),
                        azure_auth_type=AzureAuthType.SERVICE_PRINCIPAL,
                    )
                elif cert_auth := azure_auth.azure_spcert_auth:
                    azure_auth_wrap = AzureAuthWrap(
                        azure_spcert_auth=AzureAuthCertificate(
                            tenant_id=self.get_updated_content(cert_auth.tenant_id),
                            client_id=self.get_updated_content(cert_auth.client_id),
                            certificate_path=self.get_updated_content(
                                cert_auth.certificate_path
                            ),
                            scope=self.get_updated_content(
                                cert_auth.scope
                                or "https://management.azure.com/.default"
                            ),
                        ),
                        azure_auth_type=AzureAuthType.CERTIFICATE,
                    )
                elif azure_auth.azure_cli_auth:
                    azure_auth_wrap = AzureAuthWrap(
                        azure_cli_auth=AzureAuthCli(
                            scope=self.get_updated_content(
                                azure_auth.azure_cli_auth.scope
                                or "https://management.azure.com/.default"
                            )
                        ),
                        azure_auth_type=AzureAuthType.CLI,
                    )
                elif azure_auth.auth.azure_device_code:
                    azure_auth_wrap = AzureAuthWrap(
                        azure_device_code=AzureAuthDeviceCode(
                            scope=self.get_updated_content(
                                azure_auth.azure_device_code.scope
                                or "https://management.azure.com/.default"
                            )
                        ),
                        azure_auth_type=AzureAuthType.DEVICE_CODE,
                    )

                self.httpdef.auth = AzureAuth(azure_auth_wrap)

    def get_current_or_base(self, attr_key) -> Any:
        if getattr(self.http, attr_key):
            return getattr(self.http, attr_key)
        elif self.parents_http:
            for parent in self.parents_http:
                if getattr(parent, attr_key):
                    return getattr(parent, attr_key)

    def load_def(self):
        if self._loaded:
            return
        self.httpdef.name = self.args.target or "1"
        self.load_extra_flags()
        if self.httpdef.allow_insecure:
            self.property_util.enable_system_command()
            base_logger.info("allowing running system commands")
        self.load_test_script()
        # run prerequest script
        # as it will set some variables
        self.run_prerequest_script()

        self.load_method()
        self.load_url()
        self.load_headers()
        self.load_query()
        self.load_payload()
        self.load_auth()
        self.load_proxy()
        self.load_certificate()
        self.load_output()
        self._loaded = True
        self.script_execution.pre_request_script()

    def run_prerequest_script(self):
        execution_cls = (
            ScriptExecutionJs
            if self.httpdef.test_script_lang == ScriptType.JAVA_SCRIPT
            else ScriptExecutionPython
        )
        self.script_execution = execution_cls(self.httpdef, self.property_util)
        self.script_execution.init_request_script()
        for key, value in self.script_execution.client.properties.updated.items():
            self.property_util.add_command_line_property(key, value)

    def load_test_script(self):
        self.httpdef.test_script = ""
        if self.httpdef.no_parent_script:
            script_wrap: TestScript = self.http.script_wrap
        else:
            script_wrap: TestScript = self.get_current_or_base("script_wrap")
        if script_wrap and script_wrap.script:
            script = script_wrap.script[4:-2]
            self.httpdef.test_script = script.strip()
            self.httpdef.test_script_lang = ScriptType.get_script_type(
                script_type=script_wrap.lang
            )

    def load_output(self):
        if self.http.output and self.http.output.output:
            self.httpdef.output = self.http.output.output
