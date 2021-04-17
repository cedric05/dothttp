import logging
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from io import IOBase
from typing import Union, List, Optional, Dict, DefaultDict, Tuple, BinaryIO
from urllib.parse import urlencode

try:
    import jstyleson as json
    from jsonschema import validate
except:
    import json

    validate = None
from textx import TextXSyntaxError, metamodel_from_file

from .dsl_jsonparser import json_or_array_to_json
from .exceptions import *
from .parse_models import Allhttp
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
    files: Optional[
        List[Union[Tuple[str, Tuple[str, BinaryIO, Optional[str]]], Tuple[str, Tuple[None, str, None]]]]] = None


@dataclass
class HttpDef:
    name: str = None
    method: str = None
    url: str = None
    headers: dict = None
    query: dict = None
    auth: Tuple[str] = None
    payload: Optional[Payload] = None
    output: str = None

    def get_har(self):
        target = {
            "url": self.url,
            "method": self.method,
            "query": self.get_query(),
            "headers": self.get_headers(),
            "payload": self.get_payload(),
        }
        return target

    def get_payload(self):
        if not self.payload:
            return None
        payload = self.payload
        return_data = {"mimeType": self.payload.header}
        if payload.data:
            if isinstance(payload.data, dict):
                return_data["text"] = urlencode(payload.data)
            else:
                return_data["text"] = payload.data
        elif payload.json:
            return_data["text"] = json.dumps(payload.json)
        elif payload.files:
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
        with open(self.file, 'r') as f:
            self.original_content = self.content = f.read()

    def get_updated_content(self, content) -> str:
        return self.property_util.get_updated_content(content)

    def get_updated_content_object(self, content) -> str:
        return self.property_util.get_updated_content(content, 'obj')

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
        elif self.http.payload.data or self.http.payload.multi:
            data = self.http.payload.data or self.http.payload.multi[3:-3]
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
            return Payload(files=files, header=MULTIPART_FORM_INPUT)
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
