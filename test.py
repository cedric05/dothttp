from textx import metamodel_from_file, get_children_of_type
import sys

mm = metamodel_from_file('http.tx')


def apply(mm, filename):
    import requests
    with open(filename, 'r') as f:
        httpData = f.read()
    model = mm.model_from_str(httpData)
    req = requests.Request()
    req.url = model.http.url
    req.method = model.method.type if model.method else 'GET'
    headers = {}
    params = {}
    if model.lines:
        lines = model.lines.lines
        for line in lines:
            if line.query:
                params[line.query.key] = line.query.value
            else:
                headers[line.header.key] = line.header.value
    req.headers.update(headers)
    req.params.update(params)
    if (model.payload):
        if model.payload.data:
            req.data = model.payload.data
        else:
            with open(model.payload.file, 'r') as f:
                data = f.read()
            req.data = data
    session = requests.session()
    prepared = req.prepare()
    resp = session.send(prepared)
    if model.output:
        with open(model.output.output, 'w') as f:
            f.write(resp.text)
    else:
        print(resp.text)


if __name__ == "__main__":
    print(sys.argv)
    if len(sys.argv) == 2:
        print(apply(mm, sys.argv[1]))
    else:
        print(apply(mm, 'workday-upload-delete.http'))
        print('run with python test.py filename.http')
