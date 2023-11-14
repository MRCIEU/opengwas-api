import requests
import pytest


def test_login_via_link_no_names(url, headers):
    r = requests.get(url + "/users/send_verification_link?email=opengwas-ci-cd@mr-base.iam.gserviceaccount.com&dry_run=True", headers=headers)
    r2 = requests.get(r.json().get('link'), headers=headers)
    assert r2.status_code == 200 and 'name' in r2.json().get('message')


def test_send_verification_link(url, headers):
    r = requests.get(url + "/users/send_verification_link?email=test@bristol.ac.uk&dry_run=True", headers=headers)
    assert r.status_code == 200 and r.json().get('link')
    pytest.shared_variable['users_verification_link'] = r.json().get('link')


def test_login_via_link(url, headers):
    r = requests.get(pytest.shared_variable['users_verification_link'], headers)
    assert r.status_code == 200 and r.json().get('uid')
    pytest.shared_variable['users_jwt_token'] = r.json().get('token')


def test_login_by_jwt(url, headers):
    headers = {'X-Api-JWT': pytest.shared_variable['users_jwt_token']}
    r = requests.get(url + "/users/login_by_jwt", headers=headers)
    assert r.status_code == 200 and r.json().get('uid')
