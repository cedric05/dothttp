from dothttp.exceptions import *
import json
import os
import re
import sys

from curlify import to_curl
from requests import PreparedRequest, Session, Response
from textx import metamodel_from_file
import logging

from .exceptions import PropertyNotFoundException

base_logger = logging.getLogger("dothttp")
request_logger = logging.getLogger("request")
curl_logger = logging.getLogger("curl")


dir_path = os.path.dirname(os.path.realpath(__file__))

dothttp_model = metamodel_from_file(os.path.join(dir_path, 'http.tx'))


class BaseModelProcessor:
    var_regex = re.compile(r'{(?P<varible>\w*)}')

    def load_properties(self):
        if not self.property_file:
            base_logger.debug('properfile not specified')
            default = os.path.join(os.path.dirname(self.file), ".dothttp.json")
            if os.path.exists(default):
                base_logger.debug(
                    f'file: {default} exists. it will be used for property reference')
                self.property_file = default
        elif not os.path.exists(self.property_file):
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
                except:
                    raise PropertyFileNotJsonException(
                        propertyfile=self.property_file)
        else:
            props = {}
        self.properties.update(props.get("*", {}))
        if self.env:
            for env_name in self.env:
                self.properties.update(props.get(env_name, {}))
        return self.properties

    def __init__(self, args):
        self.args = args
        self.file = args.file
        self.properties = {}
        self.property_file = args.property_file
        self.env = args.env
        self.content = ''
        self.model = None
        self.load()

    def load(self):
        self.load_content()
        self.load_properties()
        self.update_content_with_prop()
        self.load_model()

    def load_model(self):
        # TODO for a very big file, it could be a problem
        # textx has provided utitlity to load model, but we had variable options
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
            self.content = f.read()

    def update_content_with_prop(self):
        out = BaseModelProcessor.var_regex.findall(self.content)
        base_logger.debug(f'propertys used in `{self.file}` are `{out}`')
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
        if data := self.model.payload.data:
            request_logger.debug(
                f'payload for request is `{data}`')
            return data
        elif filename := self.model.payload.file:
            request_logger.debug(
                f'payload will be loaded from `{filename}`')
            if not os.path.exists(filename):
                request_logger.debug(
                    f'payload file `{filename}` Not found. ')
                raise DataFileNotFoundException(datafile=filename)
            with open(filename, 'r') as f:
                return f.read()

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
        prep.prepare_body(self.get_payload(), None)
        request_logger.debug(f'request prepared completely')
        return prep

    def run(self):
        raise NotImplementedError()


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
