import sys
sys.path.append('..')
import pytest
import json

from filelock import FileLock

from resources.globals import Globals
from apis.tests.token import get_token


collect_ignore = ["test_db_content.py", "test_quality_control.py"]


def pytest_configure():
    pytest.shared_variable = {}
    # sys.stdout = sys.stderr  # Redirect stdout to stderr to ensure print statements are captured when running with x-dist


def pytest_addoption(parser):
    parser.addoption(
        "--url", action="store", default="http://0.0.0.0:8019/api",
        help="URL to look for the deployed API. Default is local test http://0.0.0.0:8019/api"
    )


@pytest.fixture
def url(request):
    return request.config.getoption("--url").rstrip("/")


@pytest.fixture(scope="session")
def headers(tmp_path_factory, worker_id):
    # For API tests here, X-TEST-NO-RATE-LIMIT-KEY is provided to bypass flask-limiter while JWT is for authentication
    # For tests from clients e.g. ieugwasr, X-TEST-MODE-KEY is for bypassing flask-limiter and also for authentication, and there is no need to provide JWT. However, when provided, JWT will be used for authentication
    # See app/middleware/auth.py and app/apis/tests/test_user.py

    # https://pytest-xdist.readthedocs.io/en/stable/how-to.html#making-session-scoped-fixtures-execute-only-once
    if worker_id == "master":
        # there is only one worker i.e. x-dist inactive
        token = get_token()
    else:
        # x-dist
        # get the temp directory shared by all workers
        fn = tmp_path_factory.getbasetemp().parent / "token.json"
        with FileLock(str(fn) + ".lock"):
            if fn.is_file():
                token = json.loads(fn.read_text())['token']
            else:
                token = get_token()
                fn.write_text(json.dumps({'token': token}))

    return {
        'X-TEST-NO-RATE-LIMIT-KEY': Globals.app_config['test']['no_rate_limit_key'],
        'Authorization': 'Bearer ' + token
    }
