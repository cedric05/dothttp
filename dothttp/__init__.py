import os
import re
import sys

from curlify import to_curl
from requests import PreparedRequest, Session, Response
from textx import metamodel_from_file, model as Model

dir_path = os.path.dirname(os.path.realpath(__file__))

mm = metamodel_from_file(os.path.join(dir_path, 'http.tx'))
var_regex = re.compile(r'{(?P<varible>\w*)}')


class BaseModelProcessor:
    def __init__(self, model: Model):
        self.model = model

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


class CurlCompiler(BaseModelProcessor):

    def run(self):
        prep = self.get_request()
        output = self.get_output()
        curlreq = to_curl(prep)
        if 'b' in output.mode:
            curlreq = curlreq.encode()
        output.write(curlreq)
        if output.fileno() != 1:
            output.close()


class RequestCompiler(BaseModelProcessor):

    def run(self):
        session = Session()
        resp: Response = session.send(self.get_request())
        output = self.get_output()
        for data in resp.iter_content():
            if 'b' in output.mode:
                output.write(data)
            else:
                output.write(data.decode())
        if output.fileno() != 1:
            output.close()


def apply(mm, filename):
    with open(filename, 'r') as f:
        httpData = f.read()
    model = mm.model_from_str(httpData)
    RequestCompiler(model).run()


if __name__ == "__main__":
    if len(sys.argv) == 2:
        print(apply(mm, sys.argv[1]))
    else:
        print(apply(mm, "..\examples\dothttpazure.http"))
        print('run with python test.py filename.http')
