from textx import metamodel_from_file, get_children_of_type
import sys

mm = metamodel_from_file('http.tx')



def apply(mm, filename):
    import requests
    with open(filename,'r') as f:
        httpData = f.read()
    model =mm.model_from_str(httpData)
    req = requests.Request()
    req.url = model.http.url
    req.method = model.method.type if model.method else 'GET'
    if model.headerlist:
        for header in model.headerlist.headers:
            req.headers[header.key] = header.value
    if model.querylist:
        req.params = {}
        for query in model.querylist.querys:
            req.params[query.key] = query.value
    session = requests.session()
    prepared = req.prepare()
    return session.send(prepared)

print(sys.argv)
if len(sys.argv)  == 2:
    print(apply(mm, sys.argv[1]).text)
else:
    print('run with python test.py filename.http')