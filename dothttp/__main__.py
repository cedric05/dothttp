from . import RequestCompiler, CurlCompiler, dothttp_model
import sys


def apply(mm, filename):
    with open(filename, 'r') as f:
        httpData = f.read()
    model = mm.model_from_str(httpData)
    RequestCompiler(model).run()


if __name__ == "__main__":
    if len(sys.argv) == 2:
        print(apply(dothttp_model, sys.argv[1]))
    else:
        print(apply(dothttp_model, "..\examples\dothttpazure.http"))
        print('run with python test.py filename.http')
