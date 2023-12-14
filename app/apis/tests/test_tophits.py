import requests


# Anonymous
def test_tophits_post0(url, headers):
    del headers['Authorization']
    payload = {'id': ['ieu-a-2', 'ieu-a-998']}
    r = requests.post(url + "/tophits", data=payload, headers=headers)
    assert r.status_code == 401


# Use preclumped
def test_tophits_post1(url, headers):
    payload = {'id': ['ieu-a-2', 'ieu-a-998']}
    r = requests.post(url + "/tophits", data=payload, headers=headers)
    o = r.json()
    assert r.status_code == 200 and 70 < len(o) < 80
    assert set([x.get('id') for x in o]) == {'ieu-a-2'}


def test_tophits_post2(url, headers):
    payload = {'id': ['ieu-a-2', 'ieu-a-998'], 'preclumped': 0}
    r = requests.post(url + "/tophits", data=payload, headers=headers)
    o = r.json()
    assert r.status_code == 200 and 70 < len(o) < 80
    assert set([x.get('id') for x in o]) == {'ieu-a-2'}


def test_tophits_post3(url, headers):
    payload = {'id': ['ieu-a-2', 'ieu-a-998'], 'preclumped': 0, 'clump': 0}
    r = requests.post(url + "/tophits", data=payload, headers=headers)
    o = r.json()
    assert r.status_code == 200 and len(o) > 2000
    assert set([x.get('id') for x in o]) == {'ieu-a-2'}


# Use preclumped
def test_tophits_post4(url, headers):
    payload = {'id': ['ieu-a-2', 'ieu-a-998', 'ieu-b-1']}
    r = requests.post(url + "/tophits", data=payload, headers=headers)
    o = r.json()
    assert r.status_code == 200 and 85 < len(o) < 95
    assert set([x.get('id') for x in o]) == {'ieu-a-2', 'ieu-b-1'}


def test_tophits_post5(url, headers):
    payload = {'id': ['ieu-a-2', 'ieu-a-998', 'ieu-b-1'], 'preclumped': 0}
    r = requests.post(url + "/tophits", data=payload, headers=headers)
    o = r.json()
    assert r.status_code == 200 and 85 < len(o) < 90
    assert set([x.get('id') for x in o]) == {'ieu-a-2', 'ieu-b-1'}


def test_tophits_post6(url, headers):
    payload = {'id': ['ieu-a-2', 'ieu-a-998', 'ieu-b-1'], 'preclumped': 0, 'clump': 0}
    r = requests.post(url + "/tophits", data=payload, headers=headers)
    o = r.json()
    assert r.status_code == 200 and len(o) > 2300
    assert set([x.get('id') for x in o]) == {'ieu-a-2', 'ieu-b-1'}
