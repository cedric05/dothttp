import json
import mimetypes
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import List, Iterator, Union, Dict
from urllib.parse import unquote

import requests

from dothttp import DotHttpException, HttpDef
from dothttp.request_base import RequestCompiler, Config, dothttp_model, CurlCompiler, \
    HttpFileFormatter
from dothttp.parse_models import Http, Allhttp, UrlWrap, BasicAuth, Payload, MultiPartFile, FilesWrap, Query, Header, \
    NameWrap, Line
from . import Command, Result, BaseHandler
from .postman import postman_collection_from_dict, Items, URLClass
from .utils import clean_filename

DEFAULT_URL = "https://req.dothttp.dev/"


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
        except DotHttpException as ex:
            result = Result(id=command.id,
                            result={
                                "error_message": ex.message, "error": True})
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
        config = Config(file=filename, env=envs, properties=properties, curl=curl, property_file=None, debug=True,
                        no_cookie=nocookie, format=False, info=False, target=target)
        return config

    def get_request_result(self, command, comp):
        resp = comp.get_response()
        response_data = {
            "response": {
                "headers":
                    {key: value for key, value in resp.headers.items()},
                "body": resp.text,  # for binary out, it will fail, check for alternatives
                "status": resp.status_code, }
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
        data = None
        datajson = None
        file = None
        json_payload = None
        fileswrap = None
        type = None
        if request.payload.filename:
            file = request.payload.filename
        elif isinstance(request.payload.data, str):
            data = request.payload.data
        elif isinstance(request.payload.data, dict):
            datajson = None
        elif request.payload.json:
            json_payload = request.payload.json
        elif request.payload.files:
            fileswrap = FilesWrap([])
            for filekey, multipartdata in request.payload.files:
                fileswrap.files.append(
                    MultiPartFile(name=filekey,
                                  path=multipartdata[1].name if multipartdata[0] else multipartdata[1],
                                  type=multipartdata[2] if len(multipartdata) > 2 else None)
                )

        payload = Payload(data=data, datajson=datajson, file=file, json=json_payload, fileswrap=fileswrap, type=type)

        query_lines = []
        for key, values in request.query.items():
            for value in values:
                query_lines.append(Line(header=None, query=Query(key=key, value=value)))
        return HttpFileFormatter.format(Allhttp(allhttps=[Http(
            namewrap=NameWrap(request.name),
            urlwrap=UrlWrap(url=request.url, method=request.method),
            lines=[
                      Line(header=Header(key=key, value=value), query=None)
                      for key, value in
                      request.headers.items()] + query_lines
            ,
            payload=payload,
            output=None, basic_auth_wrap=None
        )]))


class ContentBase:
    def __init__(self, config: Config):
        super().__init__(config)

    def load_content(self):
        self.original_content = self.content = self.args.file


class ContentRequestCompiler(ContentBase, RequestCompiler):
    pass


class ContentCurlCompiler(ContentBase, CurlCompiler):
    pass


class ContentExecuteHandler(RunHttpFileHandler):
    name = "/content/execute"

    def get_config(self, command):
        config = super().get_config(command)
        config.file = command.params.get('content')
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
            with open(filename) as f:
                http_data = f.read()
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
                result = Result(id=command.id, result={"names": all_names, "urls": all_urls})
        except DotHttpException as ex:
            result = Result(id=command.id,
                            result={
                                "error_message": ex.message, "error": True})
        except Exception as e:
            result = Result(id=command.id,
                            result={
                                "error_message": str(e), "error": True})
        return result


def slashed_path_to_normal_path(path):
    return path


class ImportPostmanCollection(BaseHandler):
    name = "/import/postman"

    def get_method(self):
        return ImportPostmanCollection.name

    @staticmethod
    def import_requests_into_dire(items: Iterator[Items], directory: Path, link: str):
        collection = Allhttp(allhttps=[])
        for leaf_item in items:
            onehttp = ImportPostmanCollection.import_leaf_item(leaf_item)
            if onehttp:
                collection.allhttps.append(onehttp)
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
    def import_leaf_item(item: Items) -> Union[Http, None]:
        if not item.request:
            return None
        # currently comments are not supported
        # so ignoring it for now item.description
        req = item.request
        namewrap = NameWrap(item.name)
        urlwrap = UrlWrap(url="https://", method=req.method)
        lines = []
        payload = None
        basicauthwrap = None

        if isinstance(req.url, URLClass):
            host = ".".join(req.url.host)
            proto = req.url.protocol
            path = "/".join(req.url.path)
            url = f"{proto}://{host}/{path}"
            urlwrap.url = slashed_path_to_normal_path(url)
            for query in req.url.query:
                lines.append(Line(query=Query(query.key, unquote(query.value)), header=None))
        else:
            urlwrap.url = slashed_path_to_normal_path(req.url)
        # if urlwrap.url == "":
        #     urlwrap.url = DEFAULT_URL
        if req.header:
            for header in req.header:
                lines.append(
                    Line(header=Header(key=header.key, value=slashed_path_to_normal_path(header.value)), query=None))
        if req.auth and (basic_auth := req.auth.basic):
            # TODO don't add creds to http file directly
            # add .dothttp.json file
            basicauthwrap = BasicAuth(username=basic_auth['username'], password=basic_auth['password'])
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
                payload_data = rawbody
                if optins and 'raw' in optins and 'language' in optins.get('raw'):
                    if optins['raw']['language'] == 'json':
                        try:
                            payload_json = json.loads(rawbody)
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
        http = Http(namewrap=namewrap, urlwrap=urlwrap, payload=payload, lines=lines, basic_auth_wrap=basicauthwrap,
                    output=None)
        return http

    def run(self, command: Command) -> Result:
        # params
        link: str = command.params.get("link")
        directory: str = command.params.get("directory", "")
        save = command.params.get("save", False)
        overwrite = command.params.get("overwrite", False)

        # input validations
        if save:
            if not os.path.isdir(directory):
                return Result(id=command.id, result={"error_message": "non existent directory", "error": True})
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

        resp = requests.get(link)
        postman_data = resp.json()
        if not ("info" in postman_data and 'schema' in postman_data['info'] and postman_data['info'][
            'schema'] == 'https://schema.getpostman.com/json/collection/v2.0.0/collection.json'):
            return Result(id=command.id, result={"error_message": "unsupported postman collection", "error": True})

        collection = postman_collection_from_dict(postman_data)
        d = self.import_items(collection.item, Path(directory).joinpath(clean_filename(collection.info.name)), link)
        if save:
            for path, fileout in d.items():
                if os.path.exists(path) and not overwrite:
                    p = Path(path)
                    path = p.with_stem(clean_filename(p.stem + '-' + datetime.now().ctime()))
                Path(path).parent.mkdir(parents=True, exist_ok=True)
                with open(path, 'w') as f:
                    f.write(fileout)
        return Result(id=command.id, result={"files": d})

    @staticmethod
    def import_items(items: List[Items], directory: Path, link: str = ""):
        leaf_folder = filter(lambda item: item.request, items)
        d = dict()
        d.update(ImportPostmanCollection.import_requests_into_dire(leaf_folder, directory, link))
        folder = map(lambda item: (item.name, item.item), filter(lambda item: item.item, items))
        for sub_folder, subitem in folder:
            d.update(
                ImportPostmanCollection.import_items(subitem, directory.joinpath(clean_filename(sub_folder)), link))
        return d
