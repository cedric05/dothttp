import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Iterator, Optional, Union, Dict, List
from urllib.parse import unquote, urljoin

import requests

from dothttp import Allhttp, Http, NameWrap, UrlWrap, Line, Query, Header, AuthWrap, BasicAuth, DigestAuth, \
    MultiPartFile, FilesWrap, TripleOrDouble, Certificate
from dothttp.parse_models import NtlmAuthWrap, Payload, AwsAuthWrap, HttpFileType, HawkAuth
from dothttp.request_base import HttpFileFormatter
from dothttp.utils import APPLICATION_JSON
from . import logger
from ..models import Command, Result, BaseHandler
from ..postman import Items, Auth, URLClass, POSTMAN_2, postman_collection_from_dict, AuthType, Variable, FormParameterType as FormParameterType2_0
from ..postman2_1 import FormParameterType, URLClass as URLClass_2_1, ApikeyElement, POSTMAN_2_1, \
    postman_collection21_from_dict, AuthType as AuthType_2_1
from ..utils import clean_filename, slashed_path_to_normal_path, get_alternate_filename

INHERIT_AUTH = "base-inherit-auth"

BEARER = 'Bearer'

AUTHORIZATION = 'Authorization'


class ImportPostmanCollection(BaseHandler):
    name = "/import/postman"

    def get_method(self):
        return ImportPostmanCollection.name

    @staticmethod
    def import_requests_into_dire(items: Iterator[Items], directory: Path, auth: Optional[Auth],
                                  variable: Union[None, List[Variable]], filetype: HttpFileType,
                                  link: str):
        collection = Allhttp(allhttps=[])
        base_auth_http = None
        if auth:
            base_inherit_auth_wrap, lines = ImportPostmanCollection.get_auth_wrap(auth)
            base_auth_http = Http(namewrap=NameWrap(INHERIT_AUTH), urlwrap=UrlWrap(method="GET", url="https://"),
                                  payload=None,
                                  lines=lines, authwrap=base_inherit_auth_wrap, output=None, certificate=None,
                                  description=INHERIT_AUTH)
            collection.allhttps.append(base_auth_http)
        for leaf_item in items:
            try:
                onehttp = ImportPostmanCollection.import_leaf_item(leaf_item, INHERIT_AUTH if auth else None)
                if onehttp:
                    collection.allhttps.append(onehttp)
            except:
                logger.error("import postman api failed", exc_info=True)
        d = {}
        # create file only if one or more valid collections availabile
        if not (len(collection.allhttps) == 0 or (len(collection.allhttps) == 1 and base_auth_http)):
            name = str(directory.joinpath(f'imported_from_collection.{filetype.file_exts[0]}'))
            data = HttpFileFormatter.format(collection, filetype)
            if HttpFileType.Httpfile == filetype:
                newline = os.linesep
                d[name] = f"#!/usr/bin/env dothttp{newline}{newline}" \
                          f"# imported from {link}{newline}{newline}" \
                          f"{data}{newline}"
            else:
                d[name] = data
            if variable is not None:
                dothttp_json_environment = {}
                for i in variable:
                    dothttp_json_environment[i.key] = i.value
                d[str(directory.joinpath(".dothttp.json"))] = json.dumps({"*": dothttp_json_environment})
        return d

    @staticmethod
    def import_leaf_item(item: Items, base_http_name) -> Union[Http, None]:
        if not item.request:
            return None
        # currently comments are not supported
        # so ignoring it for now item.description
        req = item.request
        request_auth = req.auth
        if req.auth and (req.auth.type == AuthType.NOAUTH or req.auth.type == AuthType_2_1.NOAUTH):
            base_http_name = None
        namewrap = NameWrap(item.name, base_http_name)
        urlwrap = UrlWrap(url="https://", method=req.method)
        payload = None

        auth_wrap, lines = ImportPostmanCollection.get_auth_wrap(request_auth)
        if isinstance(req.url, (URLClass, URLClass_2_1)):
            if host := req.url.host:
                if isinstance(host, list):
                    host = ".".join(host)
            else:
                host = "{{host}}"
            if path := req.url.path:
                if isinstance(path, list):
                    path = "/".join(path)
            else:
                path = ""
            proto = req.url.protocol or "https"
            # url = urljoin(f"{proto}://{host}", path)
            url = f"{proto}://{host}/{path}"
            urlwrap.url = slashed_path_to_normal_path(url)
            if req.url.query:
                for query in req.url.query:
                    if query.key is not None and query.value is not None:
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
                    if (one_form.type == FormParameterType.FILE) or (one_form.type == FormParameterType2_0.FILE):
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
                    output=None, certificate=certificate,
                    description=ImportPostmanCollection.extract_description(req.description))
        return http

    @staticmethod
    def extract_description(description):
        if isinstance(description, str):
            return description
        else:
            if hasattr(description, 'content'):
                return description.content
        return None

    @staticmethod
    def get_auth_wrap(request_auth):
        lines = []
        auth_wrap = None
        if request_auth:
            # TODO don't add creds to http file directly
            # add .dothttp.json file
            if basic_auth := request_auth.basic:
                # postman 2.1, it is a list of api_key_element have keys and values
                basic_auth = ImportPostmanCollection.api_key_element_to_dict(basic_auth)
                # in postman 2.0, it is a dict
                auth_wrap = AuthWrap(
                    basic_auth=BasicAuth(username=basic_auth.get('username', ''),
                                         password=basic_auth.get('password', '')))
            elif digest_auth := request_auth.digest:
                # postman 2.1, it is a list of api_key_element have keys and values
                digest_auth = ImportPostmanCollection.api_key_element_to_dict(digest_auth)
                # postman 2.0
                auth_wrap = AuthWrap(
                    digest_auth=DigestAuth(username=digest_auth.get('username', ''),
                                           password=digest_auth.get('password', '')))
            elif ntlm_auth := request_auth.ntlm:
                # postman 2.1, it is a list of api_key_element have keys and values
                ntlm_auth = ImportPostmanCollection.api_key_element_to_dict(ntlm_auth)
                # postman 2.0
                auth_wrap = AuthWrap(
                    ntlm_auth=NtlmAuthWrap(username=ntlm_auth.get('username', ''),
                                           password=ntlm_auth.get('password', '')))
            elif hawk_auth := request_auth.hawk:
                hawk_auth = ImportPostmanCollection.api_key_element_to_dict(hawk_auth)
                # postman 2.0
                auth_wrap = AuthWrap(
                    hawk_auth=HawkAuth(hawk_id=hawk_auth.get('authId', ''),
                                        key=hawk_auth.get('authKey', ''),
                                        algorithm=hawk_auth.get('algorithm', '')))
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
            elif aws_auth := request_auth.awsv4:
                aws_auth = ImportPostmanCollection.api_key_element_to_dict(aws_auth)
                accessKey = aws_auth.get("accessKey")
                secretKey = aws_auth.get("secretKey")
                region = aws_auth.get("region", 'us-east-1')
                service = aws_auth.get("service", '')
                auth_wrap = AuthWrap(
                    aws_auth=AwsAuthWrap(access_id=accessKey, secret_token=secretKey, region=region, service=service))
        return auth_wrap, lines

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
        data: str = command.params.get("postman-collection", "")
        directory: str = command.params.get("directory", "")
        save = command.params.get("save", False)
        overwrite = command.params.get("overwrite", False)
        filetype = HttpFileType.get_from_filetype(command.params.get("filetype", None))

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

        if data:
            if isinstance(data, dict):
                postman_data = data
            else:
                postman_data = json.loads(data)
            link = "dothttp_postman_import"
        else:
            if link.startswith("http"):
                postman_data = requests.get(link).json()
            else:
                with open(link) as f:
                    postman_data = json.load(f)
                link = os.path.basename(link)
        if "info" in postman_data and 'schema' in postman_data['info']:
            if postman_data['info']['schema'] == POSTMAN_2:
                collection = postman_collection_from_dict(postman_data)
                base_collection_dire = Path(directory).joinpath(clean_filename(collection.info.name))
            elif postman_data['info']['schema'] == POSTMAN_2_1:
                collection = postman_collection21_from_dict(postman_data)
                base_collection_dire = Path(directory).joinpath(clean_filename(collection.info.name))
            else:
                return Result(id=command.id, result={"error_message": "unsupported postman collection", "error": True})
            d = self.import_items(collection.item, base_collection_dire, collection.auth, collection.variable, filetype,
                                  link,
                                  )
        else:
            return Result(id=command.id, result={"error_message": "unsupported postman collection", "error": True})

        if save:
            if collection.info.description:
                base_collection_dire.mkdir(parents=True, exist_ok=True)
                with open(base_collection_dire.joinpath("README.txt"), 'w') as f:
                    f.write(ImportPostmanCollection.extract_description(collection.info.description))
            for path, fileout in d.items():
                if os.path.exists(path) and not overwrite:
                    path = get_alternate_filename(path)
                Path(path).parent.mkdir(parents=True, exist_ok=True)
                with open(path, 'w') as f:
                    f.write(fileout)
        return Result(id=command.id, result={"files": d})

    @staticmethod
    def import_items(items: List[Items], directory: Path, auth: Optional[Auth], variable, filetype: HttpFileType,
                     link: str = ""):
        leaf_folder = filter(lambda item: item.request, items)
        d = dict()
        d.update(
            ImportPostmanCollection.import_requests_into_dire(leaf_folder, directory, auth, variable, filetype, link))
        folder = map(lambda item: (item.name, item.item, item.auth), filter(lambda item: item.item, items))
        for sub_folder, subitem, item_auth in folder:
            d.update(
                ImportPostmanCollection.import_items(subitem, directory.joinpath(clean_filename(sub_folder)),
                                                     item_auth or auth, variable, filetype, link))
        return d
