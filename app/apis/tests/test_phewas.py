import requests


# Anonymous
def test_phewas_get0(url, headers):
    headers = headers.copy()
    del headers['Authorization']
    r = requests.get(url + "/phewas/rs234/0.001", headers=headers)
    assert r.status_code == 401


def test_phewas_get1(url, headers):
    r = requests.get(url + "/phewas/rs234/0.001", headers=headers)
    assert r.status_code == 200 and len(r.json()) > 20


def test_phewas_get2(url, headers):
    r = requests.get(url + "/phewas/rs234/0.01", headers=headers)
    assert r.status_code == 200 and len(r.json()) > 200


def test_phewas_post0(url, headers):
    headers = headers.copy()
    del headers['Authorization']
    payload = {'variant': 'rs234', 'pval': 0.001}
    r = requests.post(url + "/phewas", data=payload, headers=headers)
    assert r.status_code == 401


def test_phewas_post1(url, headers):
    payload = {'variant': 'rs234', 'pval': 0.001}
    r = requests.post(url + "/phewas", data=payload, headers=headers)
    assert r.status_code == 200 and len(r.json()) > 20


def test_phewas_post2(url, headers):
    payload = {'variant': 'rs234', 'pval': 0.01}
    r = requests.post(url + "/phewas", data=payload, headers=headers)
    assert r.status_code == 200 and len(r.json()) > 200


def test_phewas_post3(url, headers):
    payload = {'variant': '7:105561135', 'pval': 0.01}
    r = requests.post(url + "/phewas", data=payload, headers=headers)
    assert r.status_code == 200 and len(r.json()) > 200


def test_phewas_post4(url, headers):
    payload = {'variant': '7:105561135-105563135', 'pval': 0.01}
    r = requests.post(url + "/phewas", data=payload, headers=headers)
    assert r.status_code == 200 and len(r.json()) > 400


def test_phewas_fast_post0(url, headers):
    headers = headers.copy()
    del headers['Authorization']
    payload = {'variant': 'rs234', 'pval': 0.001}
    r = requests.post(url + "/phewas/fast", data=payload, headers=headers)
    assert r.status_code == 401


def test_phewas_fast_post1(url, headers):
    payload = {'variant': 'rs234', 'pval': 0.001}
    r = requests.post(url + "/phewas/fast", data=payload, headers=headers)
    assert r.status_code == 200 and len(r.json()) > 20


def test_phewas_fast_post2(url, headers):
    payload = {'variant': 'rs234', 'pval': 0.01}
    r = requests.post(url + "/phewas/fast", data=payload, headers=headers)
    assert r.status_code == 200 and len(r.json()) > 200


def test_phewas_fast_post3(url, headers):
    payload = {'variant': '7:105561135', 'pval': 0.01}
    r = requests.post(url + "/phewas/fast", data=payload, headers=headers)
    assert r.status_code == 200 and len(r.json()) > 200


def test_phewas_fast_post4(url, headers):
    payload = {'variant': '7:105561135-105563135', 'pval': 0.01}
    r = requests.post(url + "/phewas/fast", data=payload, headers=headers)
    assert r.status_code == 200 and len(r.json()) > 400
