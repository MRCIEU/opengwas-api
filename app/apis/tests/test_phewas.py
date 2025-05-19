import pytest
import requests


# Anonymous
@pytest.mark.skip
def test_phewas_get0(url, headers):
    headers = headers.copy()
    del headers['Authorization']
    r = requests.get(url + "/phewas/rs234/0.001", headers=headers)
    assert r.status_code == 401


@pytest.mark.skip
def test_phewas_get1(url, headers):
    r = requests.get(url + "/phewas/rs234/0.001", headers=headers)
    assert r.status_code == 200 and len(r.json()) > 20


@pytest.mark.skip
def test_phewas_get2(url, headers):
    r = requests.get(url + "/phewas/rs234/0.01", headers=headers)
    assert r.status_code == 200 and len(r.json()) > 200


def test_phewas_post_unauth(url, headers):
    headers = headers.copy()
    del headers['Authorization']
    payload = {'variant': 'rs234', 'pval': 0.001}
    r = requests.post(url + "/phewas", data=payload, headers=headers)
    assert r.status_code == 401


def test_phewas_post_large_pval(url, headers):
    payload = {'variant': 'rs234', 'pval': 0.01}
    r = requests.post(url + "/phewas", data=payload, headers=headers)
    assert r.status_code == 400


def test_phewas_post_too_many_records(url, headers):
    payload = {'variant': 'rs234', 'pval': 0.009}
    r = requests.post(url + "/phewas", data=payload, headers=headers)
    assert r.status_code == 400


def test_phewas_post_rsid(url, headers):
    payload = {'variant': 'rs234', 'pval': 0.0005}
    r = requests.post(url + "/phewas", data=payload, headers=headers)
    r_json = r.json()
    assert r.status_code == 200 and len(r_json) > 15 and all(float(a['p']) < 0.001 for a in r_json)


@pytest.mark.skip
def test_phewas_post2(url, headers):
    payload = {'variant': 'rs234', 'pval': 0.01}
    r = requests.post(url + "/phewas", data=payload, headers=headers)
    assert r.status_code == 200 and len(r.json()) > 200


def test_phewas_post_chrpos(url, headers):
    payload = {'variant': '7:105561135', 'pval': 0.0005}
    r = requests.post(url + "/phewas", data=payload, headers=headers)
    r_json = r.json()
    assert r.status_code == 200 and len(r_json) > 15 and all(float(a['p']) < 0.001 for a in r_json)


def test_phewas_post_cprange(url, headers):
    payload = {'variant': '7:105561135-105563135', 'pval': 0.00005}
    r = requests.post(url + "/phewas", data=payload, headers=headers)
    r_json = r.json()
    assert r.status_code == 200 and len(r_json) > 15 and all(float(a['p']) < 0.0001 for a in r_json)


def test_phewas_post_batch_filter(url, headers):
    payload = {'variant': 'rs1205', 'pval': 0.0001, 'index_list': ['ieu-a']}
    r = requests.post(url + "/phewas", data=payload, headers=headers)
    r_json = r.json()
    assert (r.status_code == 200 and len(r_json) < 5 and all(float(a['p']) < 0.0001 for a in r_json)
            and all(a['id'].startswith('ieu-a') for a in r_json))


def test_phewas_post6(url, headers):
    payload = {'variant': 'rs1693457', 'pval': 0.00000005, 'index_list': ['ubm-a']}
    r = requests.post(url + "/phewas", data=payload, headers=headers)
    assert r.status_code == 200 and len(r.json()) == 0


@pytest.mark.skip
def test_phewas_fast_post0(url, headers):
    headers = headers.copy()
    del headers['Authorization']
    payload = {'variant': 'rs234', 'pval': 0.001}
    r = requests.post(url + "/phewas/fast", data=payload, headers=headers)
    assert r.status_code == 401


@pytest.mark.skip
def test_phewas_fast_post1(url, headers):
    payload = {'variant': 'rs234', 'pval': 0.001}
    r = requests.post(url + "/phewas/fast", data=payload, headers=headers)
    assert r.status_code == 200 and len(r.json()) > 20


@pytest.mark.skip
def test_phewas_fast_post2(url, headers):
    payload = {'variant': 'rs234', 'pval': 0.01}
    r = requests.post(url + "/phewas/fast", data=payload, headers=headers)
    assert r.status_code == 200 and len(r.json()) > 200


@pytest.mark.skip
def test_phewas_fast_post3(url, headers):
    payload = {'variant': '7:105561135', 'pval': 0.01}
    r = requests.post(url + "/phewas/fast", data=payload, headers=headers)
    assert r.status_code == 200 and len(r.json()) > 200


@pytest.mark.skip
def test_phewas_fast_post4(url, headers):
    payload = {'variant': '7:105561135-105563135', 'pval': 0.01}
    r = requests.post(url + "/phewas/fast", data=payload, headers=headers)
    assert r.status_code == 200 and len(r.json()) > 400
