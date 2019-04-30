# content of conftest.py
import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--url", action="store", default="http://0.0.0.0:8019",
        help="URL to look for the deployed API. Default is local test http://0.0.0.0:8019"
    )


@pytest.fixture
def url(request):
    return request.config.getoption("--url")
