# content of conftest.py
import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--url", action="store", default="http://apitest.mrbase.org", help="my option: type1 or type2"
    )


@pytest.fixture
def url(request):
    return request.config.getoption("--url")

