import json
import os
from pathlib import Path
from typing import List, Iterator

import requests

from dothttp import HttpDef, APPLICATION_JSON, FORM_URLENCODED, Allhttp, Payload, Http
from dothttp.request_base import HttpFileFormatter
from . import logger
from ..models import Command, Result, BaseHandler
from ..models.har import Harfromdict, HarRequest


def from_har(har_format: Iterator[HarRequest]) -> List[Http]:
    """
    Returns:
        List[HttpDef]: converts har to httplist
    """
    http_list = []
    for request in har_format:
        http_def = HttpDef()
        try:
            http_def.url = request.url
            http_def.method = request.method or "GET"
            if headers := request.headers:
                http_def.headers = dict(map(lambda header: (header.name, header.value), headers))
            if queryString := request.queryString:
                http_def.query = {}
                for query in queryString:
                    if query.name in http_def.query:
                        http_def.query[query.name].append(query.value)
                    else:
                        http_def.query[query.name] = [query.value]
            if postData := request.postData:
                is_json = False
                if postData.mimeType and postData.mimeType.lower() == APPLICATION_JSON:
                    is_json = True
                payload = http_def.payload = Payload()
                if postData.text:
                    if is_json:
                        payload.header = APPLICATION_JSON
                        payload.json = json.loads(postData.text)
                    else:
                        payload.data = postData.text
                        payload.header = "text/plain"
                elif postData.params:
                    payload.header = FORM_URLENCODED
                    payload.data = postData.params
            http_def.name = request.comment
        except Exception as e:
            logger.error("import har failed", exc_info=True)
        http_list.append(http_def.get_http_from_req())
    return http_list


class Har2HttpHandler(BaseHandler):
    name = "/export/har2http"

    def run(self, command: Command) -> Result:
        params = command.params
        directory = params.get("save_directory", None)
        filename = params.get("filename", None)
        har_data = params.get("har", None)
        if filename:
            if not isinstance(filename, str):
                return Result.to_error(command, "filename is not instance of string")
            if not (os.path.isfile(filename) or (filename.startswith("http://") or filename.startswith("https://"))):
                return Result.to_error(command, "filename not existent or invalid link")
        if har_data:
            if not isinstance(har_data, (dict, list)):
                return Result.to_error(command, "har is not instance of dict")
        if (filename and har_data):
            return Result.to_error(command, "confused on which to pick filename or link")
        if not filename and not har_data:
            return Result.to_error(command, "link, har_data or filename is must")

        if directory:
            if not isinstance(directory, str):
                return Result.to_error(command, "directory is not instance of string")
            if not os.path.isdir(directory):
                return Result.to_error(command, "directory not existent")

        if filename:
            if filename.startswith("http"):
                response = requests.get(filename)
                if response.headers.get('content-type') != APPLICATION_JSON:
                    return Result.to_error(command, "content-type should be json")
                har_data = response.json()
            else:
                with open(filename) as f:
                    try:
                        har_data = json.load(f)
                    except:
                        return Result.to_error(command, "har file should be of json format")
        if isinstance(har_data, dict):
            har = Harfromdict(har_data)
            if not har.log or not har.log.entries:
                har_requests = []
            else:
                har_requests = (entry.request for entry in har.log.entries)
        else:
            har_requests = (HarRequest.from_dict(req) for req in har_data)
        http_list = from_har(har_requests)
        with open(Path(directory).joinpath("imported.http"), 'w') as f:
            output = HttpFileFormatter.format(Allhttp(allhttps=http_list))
            f.write(output)
        return Result.get_result(command, {"http": output})
        # return Result.to_error(command, "har file has not requests")
