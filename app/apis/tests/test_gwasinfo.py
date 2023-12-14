import requests


# Should return json entries for each study
def test_gwasinfo1(url, headers):
    payload = {'id': ['ieu-a-2', 'ieu-a-7']}
    r = requests.post(url + "/gwasinfo", data=payload, headers=headers)
    assert r.status_code == 200 and len(r.json()) == 2


# Should return json entries for each study
def test_gwasinfo2(url, headers):
    payload = {'id': ['ieu-a-2', 'ieu-a-7']}
    r = requests.post(url + "/gwasinfo", data=payload, headers=headers)
    assert r.status_code == 200 and len(r.json()) == 2


# Don't get private studies without authentication
def test_gwasinfo3(url, headers):
    payload = {'id': ['ieu-a-2', 'ieu-a-7', 'ieu-a-998']}
    r = requests.post(url + "/gwasinfo", data=payload, headers=headers)
    assert r.status_code == 200 and len(r.json()) == 2


# This time should have authentication to get private study
def test_gwasinfo4(url, headers):
    payload = {'id': ['ieu-a-2', 'ieu-a-7', 'ieu-a-998']}
    r = requests.post(url + "/gwasinfo", data=payload, headers=headers)
    assert r.status_code == 200 and len(r.json()) == 3


# This time should have authentication to get private study
def test_gwasinfo5(url, headers):
    payload = {}
    r = requests.post(url + "/gwasinfo", data=payload, headers=headers)
    assert r.status_code == 200 and len(r.json()) > 1000


# Using GET
def test_gwasinfo6(url, headers):
    r = requests.get(url + "/gwasinfo", headers=headers)
    assert r.status_code == 200 and len(r.json()) > 1000


# Using GET
def test_gwasinfo7(url, headers):
    r = requests.get(url + "/gwasinfo/ieu-a-2", headers=headers)
    assert r.status_code == 200 and len(r.json()) == 1


# Using GET
def test_gwasinfo8(url, headers):
    r = requests.get(url + "/gwasinfo/ieu-a-2,ieu-a-998", headers=headers)
    assert r.status_code == 200 and len(r.json()) == 1


# issue 57
def test_gwasinfo_issue_57(url, headers):
    r = requests.get(url + "/gwasinfo/ieu-a-2", headers=headers)
    assert r.status_code == 200 and len(r.json()) == 1
    assert r.json()[0]['trait'] == "Body mass index"
