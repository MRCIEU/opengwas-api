import requests
from apis.tests.token import get_mrbase_access_token

token = get_mrbase_access_token()

## GET


def test_assoc_get1(url):
    r = requests.get(url + "/associations/ieu-a-2/rs234")
    assert r.status_code == 200 and len(r.json()) == 1


def test_assoc_get2(url):
    r = requests.get(url + "/associations/ieu-a-300/rs4988235")
    assert r.status_code == 200 and len(r.json()) == 1


def test_assoc_get3(url):
    r = requests.get(url + "/associations/ieu-a-2,ieu-a-998/rs234")
    assert r.status_code == 200 and len(r.json()) == 1


def test_assoc_get4(url):
    r = requests.get(url + "/associations/ieu-a-2,ieu-a-998,ieu-a-7/rs234")
    assert r.status_code == 200 and len(r.json()) == 2


def test_assoc_get5(url):
    r = requests.get(url + "/associations/ieu-a-2,ieu-a-998,ieu-a-7/rs234,rs123")
    assert r.status_code == 200 and len(r.json()) == 4


def test_assoc_get6(url):
    r = requests.get(url + "/associations/ieu-a-2,ieu-a-998,ieu-a-7/rs234,rs123")
    assert r.status_code == 200 and len(r.json()) >= 6


## POST

# Should return json entries for each study
def test_assoc_post1(url):
    payload = {'id': ['ieu-a-2', 'ieu-a-7', 'ieu-a-998'], 'variant': ['rs234', 'rs123']}
    r = requests.post(url + "/associations", data=payload)
    assert r.status_code == 200 and len(r.json()) == 4


def test_assoc_post2(url):
    payload = {'id': ['ieu-a-2', 'ieu-a-7', 'ieu-a-998'], 'variant': ['rs234', 'rs123']}
    r = requests.post(url + "/associations", data=payload)
    assert r.status_code == 200 and len(r.json()) >= 6


def test_assoc_post3(url):
    payload = {'id': ['ieu-a-1', 'ieu-a-2'], 'variant': ['rs6689306']}
    r = requests.post(url + "/associations", data=payload)
    assert r.status_code == 200 and len(r.json()) == 0


def test_assoc_post4(url):
    payload = {'id': ['ieu-a-1', 'ieu-a-2'], 'variant': ['rs6689306'], 'proxies': 1}
    r = requests.post(url + "/associations", data=payload)
    assert r.status_code == 200 and len(r.json()) == 2


def test_assoc_post5(url):
    payload = {'id': ['ieu-a-1', 'ieu-a-2'], 'variant': ['rs234', 'rs123', 'rs6689306']}
    r = requests.post(url + "/associations", data=payload)
    assert r.status_code == 200 and len(r.json()) == 4


def test_assoc_post6(url):
    payload = {'id': ['ieu-a-1', 'ieu-a-2'], 'variant': ['rs234', 'rs123', 'rs6689306'], 'proxies': 1}
    r = requests.post(url + "/associations", data=payload)
    assert r.status_code == 200 and len(r.json()) == 6

# chrpos


def test_chrpos1(url):
    payload = {'id': ['ieu-a-2'], 'variant': ['7:105561135'], 'proxies': 0}
    r1 = requests.post(url + "/associations", data=payload).json()
    payload = {'id': ['ieu-a-2'], 'variant': ['rs234'], 'proxies': 0}
    r2 = requests.post(url + "/associations", data=payload).json()

    assert r1[0]['rsid'] == r2[0]['rsid']


def test_chrpos2(url):
    payload = {'id': ['ieu-a-2'], 'variant': ['7:105561135', 'rs1205'], 'proxies': 0}
    r1 = requests.post(url + "/associations", data=payload).json()
    payload = {'id': ['ieu-a-2'], 'variant': ['rs234'], 'proxies': 0}
    r2 = requests.post(url + "/associations", data=payload).json()

    assert len(r1) == 2


def test_chrpos3(url):
    payload = {'id': ['ieu-a-2'], 'variant': ['7:105561135-105571135', 'rs1205'], 'proxies': 0}
    r1 = requests.post(url + "/associations", data=payload).json()
    assert 'rs1205' in [x['rsid'] for x in r1]
    assert len(r1) > 1
