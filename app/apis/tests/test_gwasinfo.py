import requests
from apis.tests.token import get_mrbase_access_token

token = get_mrbase_access_token()

# Should return json entries for each study
def test_gwasinfo1(url):
    payload = {'id': ['ieu-a-2', 'ieu-a-7']}
    r = requests.post(url + "/gwasinfo", data=payload)
    assert r.status_code == 200 and len(r.json()) == 2


# Should return json entries for each study
def test_gwasinfo2(url):
    payload = {'id': ['ieu-a-2', 'ieu-a-7']}
    r = requests.post(url + "/gwasinfo", data=payload)
    assert r.status_code == 200 and len(r.json()) == 2


# Don't get private studies without authentication
def test_gwasinfo3(url):
    payload = {'id': ['ieu-a-2', 'ieu-a-7', 'ieu-a-987']}
    r = requests.post(url + "/gwasinfo", data=payload)
    assert r.status_code == 200 and len(r.json()) == 2


# This time should have authentication to get private study
def test_gwasinfo4(url):
    headers = {'X-API-TOKEN': token}
    payload = {'id': ['ieu-a-2', 'ieu-a-7', 'ieu-a-987']}
    r = requests.post(url + "/gwasinfo", data=payload, headers=headers)
    assert r.status_code == 200 and len(r.json()) == 3


# This time should have authentication to get private study
def test_gwasinfo5(url):
    headers = {'X-API-TOKEN': token}
    payload = {}
    r = requests.post(url + "/gwasinfo", data=payload, headers=headers)
    assert r.status_code == 200 and len(r.json()) > 1000


# Using GET
def test_gwasinfo6(url):
    r = requests.get(url + "/gwasinfo")
    assert r.status_code == 200 and len(r.json()) > 1000


# Using GET
def test_gwasinfo7(url):
    r = requests.get(url + "/gwasinfo/ieu-a-2")
    assert r.status_code == 200 and len(r.json()) == 1


# Using GET
def test_gwasinfo8(url):
    r = requests.get(url + "/gwasinfo/ieu-a-2,ieu-a-987")
    assert r.status_code == 200 and len(r.json()) == 1


# issue 57
def test_gwasinfo_issue_57(url):
    r = requests.get(url + "/gwasinfo/ieu-a-2")
    assert r.status_code == 200 and len(r.json()) == 1
    assert r.json()[0]['trait'] == "Body mass index"
