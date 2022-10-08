import glob
import os
import pathlib
import urllib.parse
from typing import Dict

from requests.auth import HTTPBasicAuth, HTTPDigestAuth
from requests_hawk import HawkAuth as RequestsHawkAuth
from dothttp import HttpNtlmAuth

from dotextensions.server.postman2_1 import FormParameterType, File, Mode, AuthType, Variable
from dothttp import json_or_array_to_json, UndefinedHttpToExtend, ParameterException, HttpDef, \
    request_logger, Payload, APPLICATION_JSON, CONTENT_TYPE, AWS4Auth, dothttp_model
from dothttp.parse_models import NtlmAuthWrap
from dothttp.request_base import RequestCompiler
from dothttp.utils import json_to_urlencoded_array
from . import logger
from .basic_handlers import RunHttpFileHandler
from ..models import Command, Result
from ..postman2_1 import RequestClass, Items, Auth, ApikeyElement, Header, QueryParam, URLClass, \
    Information, POSTMAN_2_1, PostmanCollection21, Body, FormParameter, URLEncodedParameter

try:
    import jstyleson as json
except:
    import json


class PostManCompiler(RequestCompiler):
    def __init__(self, config, model):
        self.model = model
        super(PostManCompiler, self).__init__(config)

    def load_content(self):
        return

    def get_updated_content_object(self, content) -> str:
        return content

    def get_updated_content(self, content) -> str:
        return content

    def load_model(self):
        return

    def validate_names(self):
        pass

    def load_payload_fileinput(self, upload_filename):
        upload_filename = self.get_updated_content(upload_filename)
        request_logger.debug(
            f'payload will be loaded from `{upload_filename}`')
        return Payload(data=None, header=None, filename=upload_filename)


def has_file_type(root_path, file_type):
    it = glob.iglob(os.path.join(root_path, file_type), recursive=True)
    if next(it, None):
        it.close()
        return True
    return False


class Http2Postman(RunHttpFileHandler):
    name = "/export/http2postman"

    def get_method(self):
        return Http2Postman.name

    @staticmethod
    def contains_http_files(path):
        # return has_file_type(path, f"**{os.path.sep}*.{{http,dhttp}}")
        return has_file_type(path, f"**{os.path.sep}*.http") or has_file_type(path, f"**{os.path.sep}*.dhttp")

    def run(self, command: Command) -> Result:
        params = command.params
        filename = params.get("filename", None)
        content = params.get("content", None)
        params['file'] = filename
        config = self.get_config(command)
        try:
            if content:
                # for content and filename
                # scenario, we need both
                # for export
                if not isinstance(content, str):
                    return Result.to_error(command, "content is not instance of string")
            elif filename:
                if not isinstance(filename, str):
                    return Result.to_error(command, "filename is not instance of string")
                if not (os.path.isfile(filename) or os.path.isdir(filename)):
                    return Result.to_error(command, "filename not existent or invalid link")
            else:
                raise Result.to_error(command, "filename is not sent")
        except Exception as e:
            return Result.to_error(command, f"unable to parse because of parsing issues {e}")
        if content:
            item = self.get_collection_item_for_file(config, filename, content)
            collection = self.get_default_collection(filename)
            collection.item = item.item
            collection.variable = item.variable or None
        elif os.path.isfile(filename):
            try:
                with open(filename) as f:
                    item = self.get_collection_item_for_file(config,
                                                             filename,
                                                             f.read()
                                                             )
                    collection = self.get_default_collection(filename)
                    collection.item = item.item
                    collection.variable = item.variable or None
            except Exception as e:
                logger.warning("not able to retrieve collections", exc_info=True)
                return Result.to_error(command, f"unable to parse because of parsing issues {e}")
        else:
            root_path_to_item_dict: Dict[str, Items] = dict()
            for root, dirs, files in os.walk(filename):
                if not Http2Postman.contains_http_files(root):
                    continue
                root_collection: Items = root_path_to_item_dict.get(root, None)
                if not root_collection:
                    root_path_to_item_dict[root] = root_collection = Items.from_dict(
                        {"item": [],
                         "name": os.path.basename(root)
                         })
                dirs.sort()
                files.sort()
                for dir_name in dirs:
                    dir_full_path = os.path.join(root, dir_name)
                    if Http2Postman.contains_http_files(dir_full_path):
                        root_collection.item.append(Items.from_dict({"item": [], "name": dir_name}))
                        root_path_to_item_dict[dir_full_path] = root_collection.item[-1]
                for one_file in files:
                    if one_file.endswith(".http") or one_file.endswith(".dhttp"):
                        try:
                            with open(os.path.join(root, one_file)) as f:
                                file_collection = self.get_collection_item_for_file(config,
                                                                                    os.path.join(root, one_file),
                                                                                    f.read())
                                root_collection.item.append(file_collection)
                        except:
                            logger.warning("not able to retrieve collections", exc_info=True)
            collection = self.get_default_collection(filename)
            collection.item = [root_path_to_item_dict.get(filename)]
        return Result.get_result(command, result={"collection": collection.to_dict()})

    @staticmethod
    def get_default_collection(filename):
        collection = PostmanCollection21.from_dict({})
        collection.info = Information.from_dict({})
        collection.info.schema = POSTMAN_2_1
        collection.info.name = os.path.basename(filename) if filename else "export_from_http"
        return collection

    def get_collection_item_for_file(self, config, filename, content):
        # http_type = HttpFileType.get_format_from_file_name(filename)
        # if http_type == HttpFileType.Httpfile:
        #     http_list = dothttp_model.model_from_str(content)
        # else:
        #     http_list = []
        #     for code in json.loads(content):
        #         if (code["kind"] == 2):
        #
        http_list = dothttp_model.model_from_str(content)
        dothttpenvjson = pathlib.Path(filename).parent.joinpath('.dothttp.json')
        item_list = Items.from_dict({"item": [], "variable": [], "name": os.path.basename(filename)})
        if dothttpenvjson.exists():
            with open(dothttpenvjson, 'r') as f:
                try:
                    # will export all variables from .dothttp.json
                    # and will enable only "*" environment
                    # variables from rest environments will be in disabled state
                    dothttpenv = json.load(f)
                    if dothttpenv:
                        for environment in dothttpenv.keys():
                            for key, value in dothttpenv[environment].items():
                                item_list.variable.append(
                                    Variable.from_dict(
                                        {"key": key, "value": value, "disabled": environment != "*"}))

                except:
                    pass
        for index, http in enumerate(http_list.allhttps):
            try:
                name = http.namewrap.name if http.namewrap else str(index + 1)
                config.target = name
                req_comp = PostManCompiler(config, http_list)
                req_comp.load()
                req_comp.load_def()
                item = Items.from_dict({})
                item.name = name
                item_list.item.append(item)
                item.request = self.get_http_to_postman_request(req_comp.httpdef, name)
            except (UndefinedHttpToExtend, ParameterException) as e:
                logger.warning(f"happens when wrongly configured, ignoring with {e}", exc_info=True)
            except Exception as e:
                logger.warning(f"unknown errors happened, will export rest {e}", exc_info=True)
        return item_list

    @staticmethod
    def get_http_to_postman_request(http: HttpDef, description="") -> RequestClass:
        request = RequestClass.from_dict({})
        request.url = http.url
        request.method = http.method
        if auth := http.auth:
            request.auth = Auth.from_dict({})
            if isinstance(auth, (HTTPBasicAuth, HTTPDigestAuth, HttpNtlmAuth)):
                request_auth = []
                if isinstance(auth, HTTPBasicAuth):
                    request.auth.basic = request_auth
                    request.auth.type = AuthType.BASIC
                elif isinstance(auth, HTTPDigestAuth):
                    request.auth.digest = request_auth
                    request.auth.type = AuthType.DIGEST
                elif isinstance(auth, HttpNtlmAuth):
                    request.auth.ntlm = request_auth
                    request.auth.type = AuthType.NTLM
                request_auth += [ApikeyElement(
                    key="username",
                    value=auth.username,
                    type="string"
                ), ApikeyElement(key="password", value=auth.password, type="string")]
            if isinstance(auth, RequestsHawkAuth):
                request_auth = []
                request.auth.hawk = request_auth
                request.auth.type = AuthType.HAWK
                hawk_id = auth.credentials.get("id", "")
                hawk_key = auth.credentials.get("key", "")
                hawk_algorithm = auth.credentials.get("algorithm", "")
                request_auth += [ApikeyElement(
                    key="hawkId",
                    value=hawk_id,
                    type="string"
                ), 
                ApikeyElement(key="authKey", value=hawk_key, type="string"),
                ApikeyElement(key="algorithm", value=hawk_algorithm, type="string")]
            elif isinstance(auth, AWS4Auth):
                request.auth.type = AuthType.AWSV4
                request.auth.awsv4 = [
                    ApikeyElement(
                        key="accessKey",
                        value=auth.access_id,
                        type="string"
                    ),
                    ApikeyElement(
                        key="secretKey",
                        value=auth.signing_key.secret_key,
                        type="string"
                    ),
                    ApikeyElement(
                        key="region",
                        value=auth.region,
                        type="string"
                    ),
                    ApikeyElement(
                        key="service",
                        value=auth.service,
                        type="string"
                    ),
                ]
        if http.headers:
            request.header = list(map(lambda key:
                                      Header(description=None, disabled=False, key=key[0],
                                             value=key[1]),
                                      http.headers.items()))
        if http.query:
            query = []
            for key, values in http.query.items():
                for value in values:
                    query.append(QueryParam(description=None, disabled=False, key=key,
                                            value=value))
            request.url = URLClass.from_dict({})
            parsed_url = urllib.parse.urlparse(http.url)
            # query not from url will be placed in query
            request.url.path = parsed_url.path
            request.url.host = parsed_url.hostname
            try:
                if isinstance(parsed_url.port, int):
                    request.url.port = str(parsed_url.port)
            except ValueError:
                request.url.port = None
            request.url.protocol = parsed_url.scheme
            request.url.query = query
            for key, value in urllib.parse.parse_qsl(parsed_url.query):
                query.append(QueryParam(description=None, disabled=None, value=value, key=key))
            request.url.query = query
            request.url.raw = http.url
        if payload := http.payload:
            body = Body.from_dict({})
            if isinstance(payload.data, dict):
                body.mode = Mode.URLENCODED
                body.urlencoded = [URLEncodedParameter(description=None, disabled=None, key=key, value=val) for
                                   key, val in
                                   # json to key value pairs
                                   json_to_urlencoded_array(
                                       # textx object to json
                                       json_or_array_to_json(payload.data, lambda k: k))]
                request.body = body
            elif json_payload := payload.json:
                body.mode = Mode.RAW
                body.options = {"language": "json"}
                body.raw = json.dumps(json_or_array_to_json(json_payload, lambda x: x))
                if not request.header:
                    request.header = []
                request.header.append(Header(description=None, disabled=False, key=CONTENT_TYPE,
                                             value=APPLICATION_JSON))
                request.body = body
            elif file_path := payload.filename:
                body.mode = Mode.FILE
                body.file = File(content="", src=file_path)
                request.body = body
            elif data := payload.data:
                body.mode = Mode.RAW
                body.raw = data
                request.body = body
            elif form := payload.files:
                body.mode = Mode.FORMDATA
                body.formdata = []
                for key, value in form:
                    (filename, content, datatype) = value
                    form = FormParameter.from_dict({})
                    form.key = key
                    if filename:
                        form.type = FormParameterType.FILE
                        form.value = filename
                    else:
                        form.type = FormParameterType.TEXT
                        form.value = content
                    form.content_type = datatype
                    body.formdata.append(form)
                request.body = body
        request.description = description
        return request
