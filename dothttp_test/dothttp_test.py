import os
from collections import namedtuple
import logging

from dothttp.parse import (
    Config,
)
from dothttp.parse.request_base import (
    RequestCompiler,
    dothttp_model,
)
from dotextensions.server.handlers.basic_handlers import RunHttpFileHandler


LOGGER = logging.getLogger(__name__)


HttpDefTest = namedtuple(
    "HttpDef", ["display", "file", "name", "config", "failed"])


def pytest_generate_tests(metafunc):
    prefix = metafunc.config.getoption("prefix")
    directory = metafunc.config.getoption("directory")
    # iterate through all sub directories in the directory
    # and get all httpdef files
    # and pass it to the test function
    tests_to_run = []

    for dir in directory:
        if not os.path.exists(dir):
            LOGGER.error(f"{dir} does not exists")
            continue
        if os.path.isfile(dir):
            tests_to_run += extrct_tests_to_run(metafunc,
                                                prefix, dir)
        else:
            for root, _dirs, files in os.walk(dir):
                for filename in files:
                    tests_to_run += extrct_tests_to_run(
                        metafunc, prefix, os.path.join(root, filename))
    metafunc.parametrize("httpdeftest", tests_to_run, ids=lambda x: x.display)


def extrct_tests_to_run(metafunc, prefix, filename):
    tests_to_run = []
    if filename.endswith(".http"):
        with open(os.path.join(filename)) as f:
            httpdef = f.read()
        try:
            model = dothttp_model.model_from_str(httpdef)
            for http in model.allhttps:
                if prefix is not None:
                    if prefix == "*":
                        tests_to_run.append(
                            HttpDefTest(
                                file=filename,
                                name=http.namewrap.name,
                                display=f"{filename} - name={http.namewrap.name}",
                                config=metafunc.config,
                                failed=False
                            )
                        )
                    elif http.namewrap and http.namewrap.name.startswith(prefix):
                        tests_to_run.append(
                            HttpDefTest(
                                file=filename,
                                name=http.namewrap.name,
                                display=f"{filename} - name={http.namewrap.name}",
                                config=metafunc.config,
                                failed=False
                            )
                        )
        except:
            tests_to_run.append(
                HttpDefTest(
                    file=filename,
                    name="entire_file",
                    display=f"{filename} - name='entire_file'",
                    config=metafunc.config,
                    failed=True
                )
            )
            LOGGER.error(f"error in parsing {filename}")
    return tests_to_run


def test_httpdef(httpdeftest: HttpDefTest):
    if httpdeftest.failed:
        assert False, "failed to parse"
    # read below arguments from command line
    config = Config(
        file=httpdeftest.file,
        target=httpdeftest.name,
        property_file=httpdeftest.config.getoption("property_file"),
        env=httpdeftest.config.getoption("env"),
        properties=httpdeftest.config.getoption("property"),
        debug=True,
        info=True,
        curl=False,
        no_cookie=False,
        format=False,
    )
    comp = RequestCompiler(config)

    realized_http_def_content = RunHttpFileHandler.get_http_from_req(
        comp.httpdef)

    logging.warning(
        f"realized_http_def_content {realized_http_def_content}",
    )

    resp = comp.get_response()

    logging.info(f"resp={resp}")

    script_result = comp.script_execution.execute_test_script(resp)

    for test in script_result.tests:
        # at present only one failure is reported in the test.
        # if there are multiple failures, only the first one is reported
        logging.warning(
            f"script_result: test={test}, test_success: {test.success}, error:{test.error}",
        )
        assert test.success, test.error
