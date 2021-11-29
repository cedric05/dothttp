#!/usr/bin/env python3
import os

from dothttp import Config
from dothttp.request_base import RequestCompiler


def run_model():
    """
        main use case is to check benchmarks for loading from file to textx model
        modifying  would increase or lower performance.
    """
    filename = os.path.join(os.path.dirname(__file__), "../examples/example.http")
    envs = []
    target = "1"
    nocookie = False
    curl = False
    properties = []
    config = Config(file=filename, env=envs, properties=properties, curl=curl, property_file=None, debug=True,
                    no_cookie=nocookie, format=False, info=False, target=target)

    comp = RequestCompiler(config)
    comp.load()
    comp.load_def()
    return
