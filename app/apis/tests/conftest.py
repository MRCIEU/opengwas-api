import sys
sys.path.append('..')
import pytest

from resources.globals import Globals
from apis.tests.token import get_token


collect_ignore = ["test_quality_control.py"]


def pytest_configure():
    pytest.shared_variable = {}


def pytest_addoption(parser):
    parser.addoption(
        "--url", action="store", default="http://0.0.0.0:8019/api",
        help="URL to look for the deployed API. Default is local test http://0.0.0.0:8019/api"
    )


@pytest.fixture
def url(request):
    return request.config.getoption("--url").rstrip("/")


@pytest.fixture(scope="session")
def headers():
    # For API tests here, X-TEST-NO-RATE-LIMIT-KEY is provided to bypass flask-limiter while JWT is for authentication
    # For tests from clients e.g. ieugwasr, X-TEST-MODE-KEY is for bypassing flask-limiter and also for authentication, and there is no need to provide JWT. However, when provided, JWT will be used for authentication
    # See app/middleware/auth.py and app/apis/tests/test_user.py
    return {
        'X-TEST-NO-RATE-LIMIT-KEY': Globals.app_config['test']['no_rate_limit_key'],
        'Authorization': 'Bearer ' + get_token()
    }
