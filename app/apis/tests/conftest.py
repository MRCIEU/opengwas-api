import sys
sys.path.append('..')
import pytest
from resources.globals import Globals


collect_ignore = ["test_edit.py", "test_quality_control.py"]


def pytest_configure():
    pytest.shared_variable = {}


def pytest_addoption(parser):
    parser.addoption(
        "--url", action="store", default="http://0.0.0.0:8019/api",
        help="URL to look for the deployed API. Default is local test http://0.0.0.0:8019/api"
    )


@pytest.fixture
def url(request):
    return request.config.getoption("--url")


@pytest.fixture
def headers():
    return {
        "X-Declare-Test-Mode-Key": Globals.app_config['test']['key_declare_test_mode']
    }
