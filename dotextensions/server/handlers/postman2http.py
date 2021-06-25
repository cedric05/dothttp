import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Iterator, Optional, Union, Dict, List
from urllib.parse import unquote

import requests

from dothttp import Allhttp, Http, NameWrap, UrlWrap, Line, Query, Header, AuthWrap, BasicAuth, DigestAuth, \
    MultiPartFile, FilesWrap, TripleOrDouble, Certificate
from dothttp.parse_models import Payload
from dothttp.request_base import HttpFileFormatter
from dothttp.utils import APPLICATION_JSON
from . import logger
from ..models import Command, Result, BaseHandler
from ..postman import Items, Auth, URLClass, POSTMAN_2, postman_collection_from_dict
from ..postman2_1 import URLClass as URLClass_2_1, ApikeyElement, POSTMAN_2_1, \
    postman_collection21_from_dict
from ..utils import clean_filename, slashed_path_to_normal_path, get_alternate_filename

BEARER = 'Bearer'

AUTHORIZATION = 'Authorization'


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
                if header.key.lower() == "content-type" and header.value.lower().startswith(APPLICATION_JSON):
                    is_json_payload = True

        if request_auth:
            # TODO don't add creds to http file directly
            # add .dothttp.json file
            if basic_auth := request_auth.basic:
                # postman 2.1, it is a list of api_key_element have keys and values
                basic_auth = ImportPostmanCollection.api_key_element_to_dict(request_auth.basic)
                # in postman 2.0, it is a dict
                auth_wrap = AuthWrap(
                    basic_auth=BasicAuth(username=basic_auth.get('username', ''),
                                         password=basic_auth.get('password', '')))
            elif digest_auth := request_auth.digest:
                # postman 2.1, it is a list of api_key_element have keys and values
                digest_auth = ImportPostmanCollection.api_key_element_to_dict(request_auth.digest)
                # postman 2.0
                auth_wrap = AuthWrap(
                    digest_auth=DigestAuth(username=digest_auth.get('username', ''),
                                           password=digest_auth.get('password', '')))
            elif request_auth.apikey:
                d = ImportPostmanCollection.api_key_element_to_dict(request_auth.apikey)
                key = d.get('key', '<key>')
                value = d.get('value', '<value>')
                in_context = d.get('in', 'header')
                if in_context == "header":
                    lines.append(Line(header=Header(key, value), query=None))
                else:
                    lines.append(Line(header=None, query=Query(key, value)))
            elif request_auth.bearer:
                d = ImportPostmanCollection.api_key_element_to_dict(request_auth.bearer)
                apikey = BEARER + " " + d.get('token', '{{apikey}}')
                header = Header(key=AUTHORIZATION, value=apikey)
                lines.append(
                    Line(header=header, query=None))
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
    def api_key_element_to_dict(api_key_elements: Union[List[ApikeyElement], Dict]):
        if isinstance(api_key_elements, dict):
            return api_key_elements
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
            link = os.path.basename(link)
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
                    path = get_alternate_filename(path)
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
