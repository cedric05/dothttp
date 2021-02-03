import json
import os
import re
import sys

from curlify import to_curl
from requests import PreparedRequest, Session, Response
from textx import metamodel_from_file

from dothttp.exceptions import PropertyNotFound

dir_path = os.path.dirname(os.path.realpath(__file__))

dothttp_model = metamodel_from_file(os.path.join(dir_path, 'http.tx'))


class BaseModelProcessor:
    var_regex = re.compile(r'{(?P<varible>\w*)}')

    def load_properties(self):
        # TODO handle exceptions like file not found, non json file
        if self.property_file:
            with open(self.property_file, 'r') as f:
                props = json.load(f)
        else:
            props = {}
        self.properties.update(props.get("*", {}))
        if self.env:
            self.properties.update(props.get(self.env, {}))
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
        model = dothttp_model.model_from_str(self.content)
        self.model = model

    def load_content(self):
        with open(self.file, 'r') as f:
            self.content = f.read()

    def update_content_with_prop(self):
        out = BaseModelProcessor.var_regex.findall(self.content)
        for var in filter(lambda x: x, out):
            if var in self.properties:
                self.content = re.sub(r'{%s}' % var, self.properties.get(var), self.content)
            else:
                raise PropertyNotFound(var, self.args)


class RequestBase(BaseModelProcessor):
    def get_query(self):
        params = {}
        for line in self.model.lines:
            if query := line.query:
                params[query.key] = query.value
        return params

    def get_headers(self):
        headers = {}
        for line in self.model.lines:
            if header := line.header:
                headers[header.key] = header.value
        return headers

    def get_url(self):
        return self.model.http.url

    def get_method(self):
        if model := self.model.http.method:
            return model
        return "GET"

    def get_payload(self):
        if self.model.payload.data:
            return self.model.payload.data
        elif filename := self.model.payload.file:
            with open(filename, 'r') as f:
                return f.read()

    def get_output(self):
        if output := self.model.output:
            return open(output.output, 'wb')
        else:
            return sys.stdout

    def get_request(self):
        prep = PreparedRequest()
        prep.prepare_url(self.get_url(), self.get_query())
        prep.prepare_method(self.get_method())
        prep.prepare_headers(self.get_headers())
        prep.prepare_body(self.get_payload(), None)
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
