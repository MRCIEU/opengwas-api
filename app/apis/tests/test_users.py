import requests
import pytest


def test_signin_by_jwt(url, headers):
    headers = {'X-Api-JWT': pytest.shared_variable['users_jwt_token']}
    r = requests.get(url + "/users/signin_by_jwt", headers=headers)
    assert r.status_code == 200 and r.json().get('uid')
