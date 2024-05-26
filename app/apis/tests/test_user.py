import requests

from resources.globals import Globals


# Test whether static token is working and whether flask-limiter is disabled
def test_user_static_token(url):
    headers = {
        'X-TEST-MODE-KEY': Globals.app_config['test']['static_token']
    }
    r = requests.get(url + "/user", headers=headers)
    assert r.status_code == 200 and r.json()['user']['uid'] == Globals.app_config['test']['uid']
    assert 'X-Allowance-Limit' not in r.headers


# Test whether JWT is working and whether flask-limiter is disabled
def test_user_jwt(url, headers):
    r = requests.get(url + "/user", headers=headers)
    assert r.status_code == 200 and r.json()['user']['uid'] == Globals.app_config['test']['uid']
    assert 'X-Allowance-Limit' not in r.headers
