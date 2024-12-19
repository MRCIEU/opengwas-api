import pytest
import requests


# Anonymous
def test_gwasinfo_post0(url, headers):
    headers = headers.copy()
    del headers['Authorization']
    payload = {'id': ['ieu-a-2', 'ieu-a-7']}
    r = requests.post(url + "/gwasinfo", data=payload, headers=headers)
    assert r.status_code == 401


# Should return json entries for the study
def test_gwasinfo_post1(url, headers):
    payload = {'id': ['ieu-a-2']}
    r = requests.post(url + "/gwasinfo", data=payload, headers=headers)
    assert r.status_code == 200 and len(r.json()) == 1


# Should return json entries for each study
def test_gwasinfo_post2(url, headers):
    payload = {'id': ['ieu-a-2', 'ieu-a-7']}
    r = requests.post(url + "/gwasinfo", data=payload, headers=headers)
    assert r.status_code == 200 and len(r.json()) == 2


# Don't get studies to which the test user has no access
def test_gwasinfo_post3(url, headers):
    payload = {'id': ['ieu-a-2', 'ieu-a-7', 'ieu-a-998']}
    r = requests.post(url + "/gwasinfo", data=payload, headers=headers)
    assert r.status_code == 200 and len(r.json()) == 2


# Get authorised study
def test_gwasinfo_post4(url, headers):
    payload = {'id': ['ieu-a-2', 'ieu-a-7', 'ieu-a-998', 'ieu-b-5008']}
    r = requests.post(url + "/gwasinfo", data=payload, headers=headers)
    assert r.status_code == 200 and len(r.json()) == 3


# Get all studies incl. the authorised ones
@pytest.mark.skip
def test_gwasinfo_post5(url, headers):
    payload = {}
    r = requests.post(url + "/gwasinfo", data=payload, headers=headers)
    assert r.status_code == 200 and len(r.json()) > 48000


def test_gwasinfo_get0(url, headers):
    headers = headers.copy()
    del headers['Authorization']
    r = requests.get(url + "/gwasinfo", headers=headers)
    assert r.status_code == 401


@pytest.mark.skip
def test_gwasinfo_get1(url, headers):
    r = requests.get(url + "/gwasinfo", headers=headers)
    assert r.status_code == 200 and len(r.json()) > 48000


def test_gwasinfo_get2(url, headers):
    r = requests.get(url + "/gwasinfo/ieu-a-2", headers=headers)
    assert r.status_code == 200 and len(r.json()) == 1

    # Issue 57
    assert r.json()[0]['trait'] == "Body mass index"


def test_gwasinfo_get3(url, headers):
    r = requests.get(url + "/gwasinfo/ieu-a-2,ieu-a-998", headers=headers)
    assert r.status_code == 200 and len(r.json()) == 1


def test_gwasinfo_get4(url, headers):
    r = requests.get(url + "/gwasinfo/ieu-a-2,ieu-a-998,ieu-b-5008", headers=headers)
    assert r.status_code == 200 and len(r.json()) == 2


def test_gwasinfo_files_get0(url, headers):
    headers = headers.copy()
    del headers['Authorization']
    r = requests.get(url + "/gwasinfo/files/ieu-a-2,ieu-a-998,ieu-b-5008", headers=headers)
    assert r.status_code == 401


def test_gwasinfo_files_get1(url, headers):
    r = requests.get(url + "/gwasinfo/files/ieu-a-2,ieu-a-998,ieu-b-5008", headers=headers)
    assert r.status_code == 200 and len(r.json()) == 2
