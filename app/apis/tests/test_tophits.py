import requests
from apis.tests.token import get_mrbase_access_token

token = get_mrbase_access_token()


def test_tophits_post1(url):
    payload = {'id': ['ieu-a-2', 'ieu-a-987']}
    r = requests.post(url + "/tophits", data=payload)
    print(r.json())
    assert r.status_code == 200
    assert len(r.json()) < 3000
    assert len(set([x.get('id') for x in r.json()])) == 1

def test_tophits_post1a(url):
    payload = {'id': ['ieu-a-2', 'ieu-a-987'], 'preclumped': 0, 'clump': 1}
    r = requests.post(url + "/tophits", data=payload)
    print(r.json())
    assert r.status_code == 200
    assert len(r.json()) < 3000
    assert len(set([x.get('id') for x in r.json()])) == 1


def test_tophits_post2(url):
    headers = {'X-API-TOKEN': token}
    payload = {'id': ['ieu-a-2', 'ieu-a-987'], 'preclumped': 0, 'clump': 0}
    r = requests.post(url + "/tophits", data=payload, headers=headers)
    assert r.status_code == 200
    assert len(r.json()) > 3000
    assert len(set([x.get('id') for x in r.json()])) == 2


def test_tophits_post3(url):
    payload = {'id': ['ieu-a-2', 'ieu-a-987'], 'preclumped': 0, 'clump': 1}
    r = requests.post(url + "/tophits", data=payload)
    assert r.status_code == 200
    assert len(r.json()) < 80
    assert len(set([x.get('id') for x in r.json()])) == 1


def test_tophits_post4(url):
    headers = {'X-API-TOKEN': token}
    payload = {'id': ['ieu-a-2', 'ieu-a-987'], 'preclumped': 0, 'clump': 1}
    r = requests.post(url + "/tophits", data=payload, headers=headers)
    assert r.status_code == 200
    assert len(r.json()) > 80
    assert len(set([x.get('id') for x in r.json()])) == 2


def test_tophits_post5(url):
    headers = {'X-API-TOKEN': token}
    payload = {'id': ['ieu-a-2', 'ieu-a-987'], 'preclumped': 0}
    r = requests.post(url + "/tophits", data=payload, headers=headers)
    assert r.status_code == 200
    assert len(r.json()) > 80
    assert len(set([x.get('id') for x in r.json()])) == 2
