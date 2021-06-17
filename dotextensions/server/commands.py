import json
import logging
import mimetypes
import os
from collections import defaultdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Iterator, Union, Dict, Optional, Any
from urllib.parse import unquote

import requests
from requests import RequestException

from dothttp import DotHttpException, HttpDef, BaseModelProcessor
from dothttp.parse_models import Http, Allhttp, UrlWrap, BasicAuth, Payload, MultiPartFile, FilesWrap, Query, Header, \
    NameWrap, Line, TripleOrDouble, AuthWrap, DigestAuth, Certificate
from dothttp.request_base import RequestCompiler, Config, dothttp_model, CurlCompiler, \
    HttpFileFormatter
from . import Command, Result, BaseHandler
from .postman import postman_collection_from_dict, Items, URLClass, Auth, POSTMAN_2
from .postman2_1 import POSTMAN_2_1, postman_collection21_from_dict, ApikeyElement, URLClass as URLClass_2_1
from .utils import clean_filename

DEFAULT_URL = "https://req.dothttp.dev/"
logger = logging.getLogger('handler')


class RunHttpFileHandler(BaseHandler):
    name = "/file/execute"

    def get_method(self):
        return RunHttpFileHandler.name

    def run(self, command: Command) -> Result:
        config = self.get_config(command)
        try:
            if config.curl:
                req = self.get_curl_comp(config)
                result = req.get_curl_output()
                result = Result(id=command.id, result={
                    "body": result,
                    "headers": {
                        "Content-Type": mimetypes.types_map['.sh'],
                    }
                })
            else:
                comp = self.get_request_comp(config)
                result = self.get_request_result(command, comp)
        except DotHttpException as exc:
            logger.error(f'dothttp exception happened {exc}', exc_info=True)
            result = Result(id=command.id,
                            result={
                                "error_message": exc.message, "error": True})
        except RequestException as exc:
            logger.error(f'exception from requests {exc}', exc_info=True)
            result = Result(id=command.id,
                            result={
                                "error_message": str(exc), "error": True})
        except Exception as exc:
            logger.error(f'unknown error happened {exc}', exc_info=True)
            result = Result(id=command.id,
                            result={
                                "error_message": str(exc), "error": True})

        return result

    def get_curl_comp(self, config):
        return CurlCompiler(config)

    def get_config(self, command):
        filename = command.params.get("file")
        envs = command.params.get("env", [])
        target = command.params.get("target", '1')
        nocookie = command.params.get("nocookie", False)
        curl = command.params.get("curl", False)
        props = command.params.get('properties', {})
        properties = [f"{i}={j}" for i, j in props.items()]
        content = command.params.get("content")
        if content:
            try:
                content = "\n".join(content.splitlines())
            except:
                content = None
        config = Config(file=filename, env=envs, properties=properties, curl=curl, property_file=None, debug=True,
                        no_cookie=nocookie, format=False, info=False, target=target, content=content)
        return config

    def get_request_result(self, command, comp: RequestCompiler):
        resp = comp.get_response()
        script_result = comp.execute_script(resp).as_json()
        response_data = {
            "response": {
                "headers":
                    {key: value for key, value in resp.headers.items()},
                "body": resp.text,  # for binary out, it will fail, check for alternatives
                "status": resp.status_code,
                "method": resp.request.method,
                "url": resp.url},
            "script_result": script_result,
        }
        # will be used for response
        data = {}
        data.update(response_data['response'])  # deprecated
        data.update(response_data)
        data.update({"http": self.get_http_from_req(comp.httpdef)})
        result = Result(id=command.id,
                        result=data)
        return result

    def get_request_comp(self, config):
        return RequestCompiler(config)

    @staticmethod
    def get_http_from_req(request: HttpDef):
        http_def = request.get_http_from_req()
        return HttpFileFormatter.format(http_def)


class ContentBase:
    def __init__(self, config: Config):
        super().__init__(config)

    def load_content(self):
        self.original_content = self.content = self.args.content


class ContentRequestCompiler(ContentBase, RequestCompiler):
    pass


class ContentCurlCompiler(ContentBase, CurlCompiler):
    pass


class ContentExecuteHandler(RunHttpFileHandler):
    name = "/content/execute"

    def get_config(self, command):
        config = super().get_config(command)
        # config.file = command.params.get('content')
        return config

    def get_method(self):
        return ContentExecuteHandler.name

    def get_request_comp(self, config):
        return ContentRequestCompiler(config)

    def get_curl_comp(self, config):
        return ContentCurlCompiler(config)


class FormatHttpFileHandler(BaseHandler):
    method = "/file/format"

    def get_method(self):
        return FormatHttpFileHandler.method

    def run(self, command: Command) -> Result:
        result = Result(id=command.id, result=command.params)
        return result


class GetNameReferencesHandler(BaseHandler):
    name = "/file/names"

    def get_method(self):
        return GetNameReferencesHandler.name

    def run(self, command: Command) -> Result:
        filename = command.params.get("file")
        try:
            result = self.execute(command, filename)
        except DotHttpException as ex:
            result = Result(id=command.id,
                            result={
                                "error_message": ex.message, "error": True})
        except Exception as e:
            result = Result(id=command.id,
                            result={
                                "error_message": str(e), "error": True})
        return result

    def execute(self, command: Command, filename):
        with open(filename) as f:
            http_data = f.read()
            all_names, all_urls = self.parse_n_get(http_data)
            result = Result(id=command.id, result={"names": all_names, "urls": all_urls})
        return result

    def parse_n_get(self, http_data):
        model = dothttp_model.model_from_str(http_data)
        all_names = []
        all_urls = []
        for index, http in enumerate(model.allhttps):
            if http.namewrap:
                name = http.namewrap.name if http.namewrap else str(index)
                start = http.namewrap._tx_position
                end = http._tx_position_end
            else:
                start = http.urlwrap._tx_position
                end = http._tx_position_end
                name = str(index + 1)
            name = {
                'name': name,
                'method': http.urlwrap.method,
                'start': start,
                'end': end
            }
            url = {
                'url': http.urlwrap.url,
                'method': http.urlwrap.method or 'GET',
                'start': http.urlwrap._tx_position,
                'end': http.urlwrap._tx_position_end,
            }
            all_names.append(name)
            all_urls.append(url)
        return all_names, all_urls


class ContentNameReferencesHandler(GetNameReferencesHandler):
    name = "/content/names"

    def get_method(self):
        return ContentNameReferencesHandler.name

    def execute(self, command, filename):
        http_data = command.params.get("content", "")
        all_names, all_urls = self.parse_n_get(http_data)
        result = Result(id=command.id, result={"names": all_names, "urls": all_urls})
        return result


def slashed_path_to_normal_path(path):
    return path


class ParseHttpData(BaseHandler):
    name = "/file/parse"

    def get_method(self):
        return ParseHttpData.name

    def run(self, command: Command) -> Result:
        # certificate is not supported by har format
        # visit http://www.softwareishard.com/blog/har-12-spec/#request
        # for more information
        params = command.params
        filename = params.get("file")
        content = params.get('content')
        result = Result(id=command.id)
        if not (filename and os.path.exists(filename) and os.path.isfile(filename)) and not content:
            result.result = {"error_message": "filename or content is mandatory", "error": True}
            return result
        try:
            if filename:
                executor = RunHttpFileHandler()
            else:
                executor = ContentExecuteHandler()
            config = executor.get_config(command)
            request_compiler_obj = executor.get_request_comp(config)
            request_compiler_obj.load()
            request_compiler_obj.load_def()
            result.result = {"target": {config.target: request_compiler_obj.httpdef.get_har()}}
            return result
        except Exception as e:
            logger.error("unknown error happened", exc_info=True)
            result.result = {"error_message": str(e), "error": True}
            return result


class DothttpTypes(Enum):
    NAME = "name"
    EXTRA_ARGS = "extra_args"
    URL = "url"
    BASIC_AUTH = "basic_auth"
    DIGEST_AUTH = "digest_auth"
    CERTIFICATE = "certificate"
    HEADER = "header"
    URL_PARAMS = "urlparams"
    PAYLOAD_DATA = "payload_data"
    PAYLOAD_ENCODED = "payload_urlencoded"
    PAYLOAD_FILE = "payload_file_input"
    PAYLOAD_JSON = "payload_json"
    PAYLOAD_MULTIPART = "payload_multipart"
    OUTPUT = "output"
    SCRIPT = "script"
    COMMENT = "comment"


class TypeFromPos(BaseHandler):
    name = "/content/type"

    def get_method(self):
        return TypeFromPos.name

    def run(self, command: Command) -> Result:
        position: Union[None, int] = command.params.get("position", None)
        filename: Union[str, None] = command.params.get('filename', None)
        content: Union[str, None] = command.params.get('content', None)
        if not isinstance(position, int):
            return Result(id=command.id,
                          result={"error_message": f"position should be int", "error": True})
        if filename:
            if not isinstance(filename, str):
                return Result(id=command.id,
                              result={"error_message": f"filename should be should be string", "error": True})
            if not os.path.isfile(filename):
                return Result(id=command.id,
                              result={"error_message": f"non existant file", "error": True})
        if not filename and not content:
            return Result(id=command.id,
                          result={"error_message": f"filename or content should be available", "error": True})
        if content and not isinstance(content, str):
            return Result(id=command.id,
                          result={"error_message": f"content should be string", "error": True})
        if filename:
            model: Allhttp = dothttp_model.model_from_file(filename)
        else:
            model: Allhttp = dothttp_model.model_from_str(content)
        try:
            return Result(id=command.id, result=self.figure_n_get(model, position))
        except Exception as e:
            return Result(id=command.id, result={"error_message": f"unknown Exception {e}", "error": True})

    def figure_n_get(self, model: Allhttp, position: int) -> dict:
        if self.is_in_between(model, position):
            index = 0
            for index, pick_http in enumerate(model.allhttps):
                if self.is_in_between(pick_http, position):
                    if dot_type := self.pick_in_http(pick_http, position):
                        name = str(index + 1)
                        base = None
                        base_position = None
                        if namewrap := pick_http.namewrap:
                            name = namewrap.name
                            base = namewrap.base
                            if base:
                                try:
                                    base_position = BaseModelProcessor.get_target(base, model.allhttps)._tx_position
                                except:
                                    pass
                        return {"type": dot_type.value, "target": name, "target_base": base,
                                "base_start": base_position
                                }
        return {"type": DothttpTypes.COMMENT.value}

    @staticmethod
    def pick_in_http(pick_http: Http, position: int) -> DothttpTypes:
        self = TypeFromPos
        if pick_http:
            # order
            # name, extra args, url, basic/digest auth, certificate, query or headers, payload, output, script_wrap
            if namewrap := pick_http.namewrap:
                if self.is_in_between(namewrap, position):
                    return DothttpTypes.NAME
            if args := pick_http.extra_args:
                for arg in args:
                    if self.is_in_between(arg, position):
                        return DothttpTypes.EXTRA_ARGS
            if url_wrap := pick_http.urlwrap:
                if self.is_in_between(url_wrap, position):
                    return DothttpTypes.URL
            if auth_wrap := pick_http.authwrap:
                if auth_wrap.basic_auth:
                    if self.is_in_between(auth_wrap.basic_auth, position):
                        return DothttpTypes.BASIC_AUTH
                elif pick_http.authwrap.digest_auth:
                    if self.is_in_between(pick_http.authwrap.digest_auth, position):
                        return DothttpTypes.DIGEST_AUTH
            if certificate := pick_http.certificate:
                if self.is_in_between(certificate, position):
                    return DothttpTypes.CERTIFICATE
            if lines := pick_http.lines:
                for line in lines:
                    if self.is_in_between(line, position):
                        if self.is_in_between(line.header, position):
                            return DothttpTypes.HEADER
                        return DothttpTypes.URL_PARAMS
            if payload := pick_http.payload:
                if self.is_in_between(payload, position):
                    if payload.data:
                        return DothttpTypes.PAYLOAD_DATA
                    elif payload.datajson:
                        return DothttpTypes.PAYLOAD_ENCODED
                    elif payload.json:
                        return DothttpTypes.PAYLOAD_JSON
                    elif payload.file:
                        return DothttpTypes.PAYLOAD_FILE
                    elif payload.fileswrap:
                        return DothttpTypes.PAYLOAD_MULTIPART
                    return DothttpTypes.PAYLOAD_JSON
            if output := pick_http.output:
                if self.is_in_between(output, position):
                    return DothttpTypes.OUTPUT
            if script_wrap := pick_http.script_wrap:
                if self.is_in_between(script_wrap, position):
                    return DothttpTypes.SCRIPT

    @staticmethod
    def is_in_between(model: Any, position):
        return model and model._tx_position < position < model._tx_position_end


class ImportPostmanCollection(BaseHandler):
    name = "/import/postman"

    def get_method(self):
        return ImportPostmanCollection.name

    @staticmethod
    def import_requests_into_dire(items: Iterator[Items], directory: Path, auth: Optional[Auth], link: str):
        collection = Allhttp(allhttps=[])
        for leaf_item in items:
            try:
                onehttp = ImportPostmanCollection.import_leaf_item(leaf_item, auth)
                if onehttp:
                    collection.allhttps.append(onehttp)
            except:
                logger.error("import postman api failed", exc_info=True)
        d = {}
        if len(collection.allhttps) != 0:
            data = HttpFileFormatter.format(collection)
            name = str(directory.joinpath("imported_from_collection.http"))
            newline = "\n"
            d[name] = f"#!/usr/bin/env dothttp{newline}{newline}" \
                      f"# imported from {link}{newline}{newline}" \
                      f"{data}\n"
        return d

    @staticmethod
    def import_leaf_item(item: Items, auth: Optional[Auth]) -> Union[Http, None]:
        if not item.request:
            return None
        # currently comments are not supported
        # so ignoring it for now item.description
        req = item.request
        namewrap = NameWrap(item.name)
        urlwrap = UrlWrap(url="https://", method=req.method)
        lines = []
        payload = None
        auth_wrap = None

        request_auth = req.auth or auth

        if isinstance(req.url, (URLClass, URLClass_2_1)):
            host = ".".join(req.url.host) if req.url.host else "{{host}}"
            proto = req.url.protocol or "https"
            path = "/".join(req.url.path) if req.url.path else ""
            url = f"{proto}://{host}/{path}"
            urlwrap.url = slashed_path_to_normal_path(url)
            if req.url.query:
                for query in req.url.query:
                    if query.key and query.value:
                        lines.append(Line(query=Query(query.key, unquote(query.value)), header=None))
        else:
            urlwrap.url = slashed_path_to_normal_path(req.url)
        # if urlwrap.url == "":
        #     urlwrap.url = DEFAULT_URL
        is_json_payload = False
        if req.header:
            for header in req.header:
                lines.append(
                    Line(header=Header(key=header.key, value=slashed_path_to_normal_path(header.value)), query=None))
                if header.key.lower() == "content-type" and header.value.lower().startswith("application/json"):
                    is_json_payload = True

        if request_auth:
            # TODO don't add creds to http file directly
            # add .dothttp.json file
            if basic_auth := request_auth.basic:
                if isinstance(request_auth.basic, list):
                    # postman 2.1, it is a list of api_key_element have keys and values
                    basic_auth = ImportPostmanCollection.api_key_element_to_dict(request_auth.basic)
                # in postman 2.0, it is a dict
                auth_wrap = AuthWrap(
                    basic_auth=BasicAuth(username=basic_auth.get('username', ''),
                                         password=basic_auth.get('password', '')))
            elif digest_auth := request_auth.digest:
                if isinstance(request_auth.digest, list):
                    # postman 2.1, it is a list of api_key_element have keys and values
                    digest_auth = ImportPostmanCollection.api_key_element_to_dict(request_auth.digest)
                # postman 2.0
                auth_wrap = AuthWrap(
                    digest_auth=DigestAuth(username=digest_auth.get('username', ''),
                                           password=digest_auth.get('password', '')))
        if req.body:
            # use mode rather than None check
            mode = req.body.mode
            optins = req.body.options
            payload_fileswrap = None
            payload_file = None
            payload_data = None
            payload_json = None
            payload_datajson = None
            payload_type = None
            if formdata := req.body.formdata:
                files = []
                for one_form in formdata:
                    # TODO value can be list
                    if one_form.type == 'file':
                        # TODO according to type, you would want to normalize path
                        files.append(MultiPartFile(one_form.key, slashed_path_to_normal_path(one_form.src),
                                                   one_form.content_type))
                    else:
                        files.append(MultiPartFile(one_form.key, one_form.value, one_form.content_type))
                payload_fileswrap = FilesWrap(files)
            elif filebody := req.body.file:
                # TODO file is back slash escaped
                payload_file = slashed_path_to_normal_path(filebody.src)
            elif rawbody := req.body.raw:
                payload_data = [TripleOrDouble(str=rawbody)]
                if is_json_payload or (optins and
                                       optins.get('raw', None) and
                                       optins.get('raw').get('language', None) and
                                       optins.get('raw').get('language') == 'json'):
                    try:
                        json_payload_data = json.loads(rawbody)
                        if isinstance(json_payload_data, (dict, list)):
                            payload_json = json_payload_data
                            payload_data = None
                    except:
                        pass
            elif urlencoded_body := req.body.urlencoded:
                encodedbody: Dict[str, list] = defaultdict(lambda: [])
                for one_form_field in urlencoded_body:
                    encodedbody[one_form_field.key].append(one_form_field.value)
                payload_datajson = encodedbody
            elif req.body.graphql:
                # TODO currently not supported
                pass
            payload = Payload(datajson=payload_datajson, data=payload_data, fileswrap=payload_fileswrap,
                              json=payload_json, file=payload_file, type=payload_type)
        certificate = None
        if req.certificate and req.certificate.cert:
            certificate = Certificate(req.certificate.cert.src, req.certificate.key.src)
        http = Http(namewrap=namewrap, urlwrap=urlwrap, payload=payload, lines=lines, authwrap=auth_wrap,
                    output=None, certificate=certificate, description=req.description)
        return http

    @staticmethod
    def api_key_element_to_dict(api_key_elements: List[ApikeyElement]):
        # transforms 2.1 postman to 2.0 postman
        basic_auth = {}
        for element in api_key_elements:
            api_key_element: ApikeyElement = element
            basic_auth[api_key_element.key] = api_key_element.value
        return basic_auth

    def run(self, command: Command) -> Result:
        # params
        link: str = command.params.get("link")
        directory: str = command.params.get("directory", "")
        save = command.params.get("save", False)
        overwrite = command.params.get("overwrite", False)

        # input validations
        if save:
            if not os.path.isdir(directory):
                return Result(id=command.id,
                              result={"error_message": f"non existent directory: {directory}", "error": True})
            if not os.access(directory, os.X_OK | os.W_OK):
                return Result(id=command.id,
                              result={"error_message": "insufficient permissions", "error": True})
            if not os.path.isabs(directory):
                return Result(id=command.id,
                              result={"error_message": "expects absolute path, as server is meant to run in background",
                                      "error": True})
        # if not (link.startswith("https://www.postman.com/collections/") or link.startswith(
        #         "https://www.getpostman.com/collections")):
        #     return Result(id=command.id, result={"error_message": "not a postman link", "error": True})

        if link.startswith("http"):
            postman_data = requests.get(link).json()
        else:
            with open(link) as f:
                postman_data = json.load(f)
        base_collection_dire = ""
        if "info" in postman_data and 'schema' in postman_data['info']:
            if postman_data['info']['schema'] == POSTMAN_2:
                collection = postman_collection_from_dict(postman_data)
                base_collection_dire = Path(directory).joinpath(clean_filename(collection.info.name))
                d = self.import_items(collection.item,
                                      base_collection_dire,
                                      collection.auth,
                                      link,
                                      )
            elif postman_data['info']['schema'] == POSTMAN_2_1:
                collection = postman_collection21_from_dict(postman_data)
                base_collection_dire = Path(directory).joinpath(clean_filename(collection.info.name))
                d = self.import_items(collection.item,
                                      base_collection_dire,
                                      collection.auth,
                                      link,
                                      )
            else:
                return Result(id=command.id, result={"error_message": "unsupported postman collection", "error": True})
        else:
            return Result(id=command.id, result={"error_message": "unsupported postman collection", "error": True})

        if save:
            if collection.info.description:
                base_collection_dire.mkdir(parents=True, exist_ok=True)
                with open(base_collection_dire.joinpath("README.txt"), 'w') as f:
                    f.write(collection.info.description)
            for path, fileout in d.items():
                if os.path.exists(path) and not overwrite:
                    p = Path(path)
                    path = p.with_stem(clean_filename(p.stem + '-' + datetime.now().ctime()))
                Path(path).parent.mkdir(parents=True, exist_ok=True)
                with open(path, 'w') as f:
                    f.write(fileout)
        return Result(id=command.id, result={"files": d})

    @staticmethod
    def import_items(items: List[Items], directory: Path, auth: Optional[Auth], link: str = ""):
        leaf_folder = filter(lambda item: item.request, items)
        d = dict()
        d.update(ImportPostmanCollection.import_requests_into_dire(leaf_folder, directory, auth, link))
        folder = map(lambda item: (item.name, item.item, item.auth), filter(lambda item: item.item, items))
        for sub_folder, subitem, item_auth in folder:
            d.update(
                ImportPostmanCollection.import_items(subitem,
                                                     directory.joinpath(clean_filename(sub_folder)),
                                                     item_auth or auth,
                                                     link))
        return d
