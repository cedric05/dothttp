import os
import pathlib
import urllib.parse

from requests.auth import HTTPBasicAuth, HTTPDigestAuth

from dotextensions.server.postman2_1 import FormParameterType, File, Mode, AuthType, Variable
from dothttp import dothttp_model, json_or_array_to_json, UndefinedHttpToExtend, ParameterException, HttpDef, \
    request_logger, Payload, APPLICATION_JSON, CONTENT_TYPE, AWS4Auth
from dothttp.request_base import RequestCompiler
from dothttp.utils import json_to_urlencoded_array
from . import logger
from .basic_handlers import RunHttpFileHandler
from ..models import Command, Result
from ..postman2_1 import RequestClass, Items, Auth, ApikeyElement, Header, QueryParam, URLClass, \
    Information, POSTMAN_2_1, PostmanCollection21, Body, FormParameter, URLEncodedParameter

try:
    import jstyleson as json
    from jsonschema import validate
except:
    import json


class PostManCompiler(RequestCompiler):
    def __init__(self, config, model):
        self.model = model
        super(PostManCompiler, self).__init__(config)

    def get_updated_content_object(self, content) -> str:
        return content

    def get_updated_content(self, content) -> str:
        return content

    def load_model(self):
        return

    def load_payload_fileinput(self, upload_filename):
        upload_filename = self.get_updated_content(upload_filename)
        request_logger.debug(
            f'payload will be loaded from `{upload_filename}`')
        return Payload(data=None, header=None, filename=upload_filename)


class Http2Postman(RunHttpFileHandler):
    name = "/export/http2postman"

    def get_method(self):
        return Http2Postman.name

    def run(self, command: Command) -> Result:
        params = command.params
        filename = params.get("filename", None)
        content = params.get("content", None)
        params['file'] = filename
        config = self.get_config(command)
        variables = []
        try:
            if filename and content:
                # for content and filename
                # scenario, we need both
                # for export
                if not isinstance(content, str):
                    return Result.to_error(command, "content is not instance of string")
                http_list = dothttp_model.model_from_str(content)
            else:
                if not isinstance(filename, str):
                    return Result.to_error(command, "filename is not instance of string")
                if not (os.path.isfile(filename)):
                    return Result.to_error(command, "filename not existent or invalid link")
                http_list = dothttp_model.model_from_file(filename)
        except Exception as e:
            return Result.to_error(command, f"unable to parse because of parsing issues {e}")
        dothttpenvjson = pathlib.Path(filename).parent.joinpath('.dothttp.json')
        item_list = []
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
                                variables.append(
                                    Variable.from_dict(
                                        {"key": key, "value": value, "disabled": environment != "*"}))
                except:
                    pass
        for index, http in enumerate(http_list.allhttps):
            try:
                item = Items.from_dict({})
                item.name = http.namewrap.name if http.namewrap else ""
                config.target = item.name if item.name else str(index + 1)
                req_comp = PostManCompiler(config, http_list)
                req_comp.load()
                req_comp.load_def()
                item_list.append(item)
                item.request = self.get_http_to_postman_request(req_comp.httpdef, item.name if item.name else "")
            except (UndefinedHttpToExtend, ParameterException):
                logger.warning("happens when wrongly configured, ignoring")
            except Exception as e:
                logger.warning(f"unknown errors happened, will export rest {e}", exc_info=True)
        collection = PostmanCollection21.from_dict({})
        collection.item = item_list
        collection.info = Information.from_dict({})
        collection.info.schema = POSTMAN_2_1
        collection.variable = variables if len(variables) > 0 else None
        collection.info.name = os.path.basename(filename) if filename else "export_from_http"
        return Result.get_result(command, result={"collection": collection.to_dict()})

    def get_http_to_postman_request(self, http: HttpDef, description="") -> RequestClass:
        request = RequestClass.from_dict({})
        request.url = http.url
        request.method = http.method
        if auth := http.auth:
            request.auth = Auth.from_dict({})
            if isinstance(auth, (HTTPBasicAuth, HTTPDigestAuth)):
                if isinstance(auth, HTTPBasicAuth):
                    request_auth = request.auth.basic = []
                    request.auth.type = AuthType.BASIC
                elif isinstance(auth, HTTPDigestAuth):
                    request_auth = request.auth.digest = []
                    request.auth.type = AuthType.DIGEST
                request_auth += [ApikeyElement(
                    key="username",
                    value=auth.username,
                    type="string"
                ), ApikeyElement(key="password", value=auth.password, type="string")]
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
