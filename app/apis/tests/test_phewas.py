import requests
from apis.tests.token import get_mrbase_access_token

token = get_mrbase_access_token()


## GET

def test_phewas_get1(url):
    r = requests.get(url + "/phewas/rs234/0.001")
    assert r.status_code == 200 and len(r.json()) > 5

def test_phewas_get2(url):
    r = requests.get(url + "/phewas/rs234/0.01")
    assert r.status_code == 200 and len(r.json()) > 100


## POST

def test_phewas_post1(url):
    payload = {'variant': 'rs234', 'pval': 0.001}
    r = requests.post(url + "/phewas", data=payload)
    assert r.status_code == 200 and len(r.json()) > 5

def test_phewas_post2(url):
    payload = {'variant': 'rs234', 'pval': 0.01}
    r = requests.post(url + "/phewas", data=payload)
    assert r.status_code == 200 and len(r.json()) > 100

def test_phewas_post3(url):
    payload = {'variant': '7:105561135', 'pval': 0.01}
    r = requests.post(url + "/phewas", data=payload)
    assert r.status_code == 200 and len(r.json()) > 100

def test_phewas_post4(url):
    payload = {'variant': '7:105561135-105563135', 'pval': 0.01}
    r = requests.post(url + "/phewas", data=payload)
    assert r.status_code == 200 and len(r.json()) > 100

