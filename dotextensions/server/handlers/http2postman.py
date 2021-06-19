import json
import os
import urllib.parse

from dotextensions.server.postman2_1 import FormParameterType, File, Mode
from dothttp import dothttp_model, Http, json_or_array_to_json, triple_or_double_tostring
from ..models import BaseHandler, Command, Result
from ..postman2_1 import RequestClass, Items, Auth, ApikeyElement, Header, QueryParam, URLClass, \
    Information, POSTMAN_2_1, PostmanCollection21, Body, FormParameter, URLEncodedParameter


class Http2Postman(BaseHandler):
    name = "/export/http2postman"

    def get_method(self):
        return Http2Postman.name

    def run(self, command: Command) -> Result:
        params = command.params
        filename = params.get("filename", None)
        content = params.get("content", None)
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
        item_list = []
        for http in http_list.allhttps:
            item = Items.from_dict({})
            item_list.append(item)
            item.name = http.namewrap.name if http.namewrap else ""
            item.request = self.get_http_to_postman_request(http)
        collection = PostmanCollection21.from_dict({})
        collection.item = item_list
        collection.info = Information.from_dict({})
        collection.info.schema = POSTMAN_2_1
        collection.info.name = os.path.basename(filename) if filename else "export_from_http"
        return Result.get_result(command, result={"collection": collection.to_dict()})

    def get_http_to_postman_request(self, http: Http) -> RequestClass:
        request = RequestClass.from_dict({})
        request.url = http.urlwrap.url
        request.method = http.urlwrap.method or 'GET'
        if http.authwrap:
            request.auth = Auth.from_dict({})
            if basic_auth := http.authwrap.basic_auth:
                request.auth.basic = [ApikeyElement(
                    key="username",
                    value=basic_auth.username,
                    type="string"
                ), ApikeyElement(key="password", value=basic_auth.password, type="string")]
            else:
                digest_auth = http.authwrap.digest_auth
                request.auth.digest = [ApikeyElement(
                    key="username",
                    value=digest_auth.username,
                    type="string"
                ), ApikeyElement(key="password", value=digest_auth.password, type="string")]
        if http.lines:
            query = []
            headers = []
            for line in http.lines:
                if line.header:
                    headers.append(
                        Header(description=None, disabled=False, key=line.header.key, value=line.header.value))
                else:
                    query.append(
                        QueryParam(description=None, disabled=False, key=line.query.key, value=line.query.value))
            request.header = headers
            if query:
                request.url = URLClass.from_dict({})
                parsed_url = urllib.parse.urlparse(http.urlwrap.url)
                # query not from url will be placed in query
                request.url.path = parsed_url.path
                request.url.host = parsed_url.hostname
                request.url.port = parsed_url.port
                request.url.protocol = parsed_url.scheme
                request.url.query = query
                for key, value in urllib.parse.parse_qsl(parsed_url.query):
                    query.append(QueryParam(description=None, disabled=None, value=value, key=key))
                request.url.query = query
                request.url.raw = http.urlwrap.url
        if payload := http.payload:
            request.body = Body.from_dict({})
            if datajson := payload.datajson:
                request.body.mode = Mode.URLENCODED
                data = json_or_array_to_json(datajson, lambda k: k)
                request.body.urlencoded = [URLEncodedParameter(description=None, disabled=None, key=key, value=val) for
                                           key, val in
                                           data.items()]
            elif json_payload := payload.json:
                request.body.mode = Mode.RAW
                request.body.options = {"language": "json"}
                request.body.raw = json.dumps(json_or_array_to_json(json_payload, lambda x: x))
            elif data := payload.data:
                request.body.mode = Mode.RAW
                request.body.raw = triple_or_double_tostring(data, lambda k: k)
            elif form := payload.fileswrap:
                request.body.mode = Mode.FORMDATA
                request.body.formdata = []
                for file in form.files:
                    form = FormParameter.from_dict({})
                    form.key = file.name
                    form.type = FormParameterType.FILE if os.path.isfile(file.path) else FormParameterType.TEXT
                    form.value = file.path
                    form.content_type = file.type
                    request.body.formdata.append(form)
            elif file_path := payload.file:
                request.body.mode = Mode.FILE
                request.body.file = File(content="", src=file_path)
        request.description = '' if not http.namewrap else http.namewrap.name
        return request
