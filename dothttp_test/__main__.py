import pytest
from .conftest import *

if __name__ == "__main__":
    # run pytest with the current module
    # this will not work because of arguments
    # use `pytest dothttp_test --directory test/extensions/commands/names.http --prefix test -v -s --html=report.html`
    pytest.main(["dothttp_test", "-v", "-s", "--html=report.html"])
