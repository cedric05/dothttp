import logging
import os
import re
import sys
from dataclasses import dataclass
from typing import Union

import jstyleson as json
from curlify import to_curl
from requests import PreparedRequest, Session, Response
from textx import metamodel_from_file

from dothttp.exceptions import *
from .exceptions import PropertyNotFoundException

base_logger = logging.getLogger("dothttp")
request_logger = logging.getLogger("request")
curl_logger = logging.getLogger("curl")

dir_path = os.path.dirname(os.path.realpath(__file__))

dothttp_model = metamodel_from_file(os.path.join(dir_path, 'http.tx'))


@dataclass
class Config:
    curl: bool
    property_file: Union[str, None]
    env: list
    debug: bool
    file: str


class BaseModelProcessor:
    var_regex = re.compile(r'{(?P<varible>\w*)}')

    def load_properties(self):
        if not self.property_file:
            base_logger.debug('property file not specified')
            default = os.path.join(os.path.dirname(self.file), ".dothttp.json")
            if os.path.exists(default):
                base_logger.debug(
                    f'file: {default} exists. it will be used for property reference')
                self.property_file = default
        if not os.path.exists(self.property_file):
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
        else:
            props = {}
        self.properties.update(props.get("*", {}))
        if self.env:
            for env_name in self.env:
                self.properties.update(props.get(env_name, {}))
        return self.properties

    def __init__(self, args: Config):
        self.args = args
        self.file = args.file
        self.properties = {}
        self.property_file = args.property_file
        self.env = args.env
        self.content = ''
        self.original_content = self.content = ''
        self.load()

    def load(self):
        self.load_content()
        self.load_properties()
        self.update_content_with_prop()
        self.load_model()

    def load_model(self):
        # TODO for a very big file, it could be a problem
        # textx has provided utility to load model, but we had variable options
        # dothttp_model.model_from_file(args.file)
        try:
            model = dothttp_model.model_from_str(self.content)
        except:
            raise HttpFileSyntaxException(file=self.file, position=None)
        self.model = model

    def load_content(self):
        if not os.path.exists(self.file):
            raise HttpFileNotFoundException(file=self.file)
        with open(self.file, 'r') as f:
            self.original_content = self.content = f.read()

    def update_content_with_prop(self):
        out = BaseModelProcessor.var_regex.findall(self.content)
        base_logger.debug(f'property used in `{self.file}` are `{out}`')
        # TODO
        # print check missing properties beforehand
        # and list them, rather than fixing one by one
        for var in set(filter(lambda x: x, out)):
            if var in self.properties:
                base_logger.debug(
                    f'using `{self.properties.get(var)}` for property {var} ')
                self.content = re.sub(
                    r'{%s}' % var, self.properties.get(var), self.content)
            else:
                raise PropertyNotFoundException(
                    var=var, propertyfile=self.property_file)


class RequestBase(BaseModelProcessor):
    def get_query(self):
        params = {}
        for line in self.model.lines:
            if query := line.query:
                params[query.key] = query.value
        request_logger.debug(
            f'computed query params from `{self.file}` are `{params}`')
        return params

    def get_headers(self):
        headers = {}
        for line in self.model.lines:
            if header := line.header:
                headers[header.key] = header.value
        request_logger.debug(
            f'computed query params from `{self.file}` are `{headers}`')
        return headers

    def get_url(self):
        request_logger.debug(
            f'url is {self.model.http.url}')
        return self.model.http.url

    def get_method(self):
        if method := self.model.http.method:
            request_logger.debug(
                f'method defined in `{self.file}` is {method}')
            return method
        request_logger.debug(
            f'method not defined in `{self.file}`. defaults to `GET`')
        return "GET"

    def get_payload(self):
        if not self.model.payload:
            return None, {}, ''
        if data := self.model.payload.data:
            request_logger.debug(
                f'payload for request is `{data}`')
            return data, {}, 'data'
        elif filename := self.model.payload.file:
            request_logger.debug(
                f'payload will be loaded from `{filename}`')
            if not os.path.exists(filename):
                request_logger.debug(
                    f'payload file `{filename}` Not found. ')
                raise DataFileNotFoundException(datafile=filename)
            with open(filename, 'r') as f:
                return f.read(), {}, 'data'
        else:
            # TODO returning multiple is wrong
            # wrapping in a class is better. fix me please
            d = json_or_array_to_json(self.model.payload.json)
            return json.dumps(d), {"content-type": "application/json"}, 'json'

    def get_output(self):
        if output := self.model.output:
            request_logger.debug(
                f'output will be written into `{self.file}` is `{output}`')
            try:
                return open(output.output, 'wb')
            except:
                request_logger.debug(
                    f'not able to open `{output}`. output will be written to stdout')
                return sys.stdout
        else:
            return sys.stdout

    def get_request(self):
        prep = PreparedRequest()
        prep.prepare_url(self.get_url(), self.get_query())
        prep.prepare_method(self.get_method())
        prep.prepare_headers(self.get_headers())
        payload, headers, _ = self.get_payload()
        prep.prepare_body(payload, None)
        for key in headers:
            prep.headers[key] = headers[key]
        request_logger.debug(f'request prepared completely {prep}')
        return prep

    def run(self):
        raise NotImplementedError()


def json_or_array_to_json(model):
    if array := model.array:
        return [jsonmodel_to_json(value) for value in array.values]
    elif object := model.object:
        return {member.key: jsonmodel_to_json(member.value) for member in object.members}


def jsonmodel_to_json(model):
    if str := model.str:
        return str.value
    elif flt := model.flt:
        return flt.value
    elif bl := model.bl:
        return bl.value
    elif object := model.object:
        return {member.key: jsonmodel_to_json(member.value) for member in object.members}
    elif array := model.array:
        return [jsonmodel_to_json(value) for value in array.values]
    elif model == 'null':
        return None


class CurlCompiler(RequestBase):

    def run(self):
        prep = self.get_request()
        output = self.get_output()
        curlreq = to_curl(prep)
        if 'b' in output.mode:
            curlreq = curlreq.encode()
        output.write(curlreq)
        if output.fileno() != 1:
            output.close()
        curl_logger.debug(f'curl request generation completed successfully')


class RequestCompiler(RequestBase):

    def run(self):
        session = Session()
        resp: Response = session.send(self.get_request())
        output = self.get_output()
        for data in resp.iter_content(1024):
            if 'b' in output.mode:
                output.write(data)
            else:
                output.write(data.decode())
        if output.fileno() != 1:
            output.close()
        request_logger.debug(f'request executed completely')
