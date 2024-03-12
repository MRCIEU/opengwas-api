import pytest
import requests


# Anonymous
@pytest.mark.skip
def test_rsid_get0(url, headers):
    headers = headers.copy()
    del headers['Authorization']
    r = requests.get(url + "/variants/rsid/rs234", headers=headers)
    assert r.status_code == 401


def test_rsid_get1(url, headers):
    r = requests.get(url + "/variants/rsid/rs234", headers={})
    assert r.status_code == 200 and len(r.json()) == 1


def test_rsid_get2(url, headers):
    r = requests.get(url + "/variants/rsid/rs234,rs333", headers={})
    assert r.status_code == 200 and len(r.json()) == 2


@pytest.mark.skip
def test_chrpos_get0(url, headers):
    headers = headers.copy()
    del headers['Authorization']
    r = requests.get(url + "/variants/chrpos/7:105561135", headers=headers)
    assert r.status_code == 401


def test_chrpos_get1(url, headers):
    r = requests.get(url + "/variants/chrpos/7:105561135", headers={})
    assert r.status_code == 200 and len(r.json()) == 1


def test_chrpos_get2(url, headers):
    r = requests.get(url + "/variants/chrpos/7:105561135?radius=1000", headers={})
    assert r.status_code == 200 and len(r.json()[0]) > 1


def test_chrpos_get3(url, headers):
    r = requests.get(url + "/variants/chrpos/7:105561135-105563135,10:44865737", headers={})
    o = r.json()
    assert r.status_code == 200 and len(o) == 2
    assert len(o[0]) >= 12 or len(o[1]) >= 12


@pytest.mark.skip
def test_gene_get0(url, headers):
    headers = headers.copy()
    del headers['Authorization']
    r = requests.get(url + "/variants/gene/ENSG00000123374", headers=headers)
    assert r.status_code == 401


def test_gene_get1(url, headers):
    r = requests.get(url + "/variants/gene/ENSG00000123374", headers={})
    assert r.status_code == 200 and len(r.json()) > 15


@pytest.mark.skip
def test_rsid_post0(url, headers):
    headers = headers.copy()
    del headers['Authorization']
    payload = {'rsid': ['rs234', 'rs333']}
    r = requests.post(url + "/variants/rsid", data=payload, headers=headers)
    assert r.status_code == 401


def test_rsid_post1(url, headers):
    payload = {'rsid': ['rs234', 'rs333']}
    r = requests.post(url + "/variants/rsid", data=payload, headers={})
    assert r.status_code == 200 and len(r.json()) == 2


def test_chrpos_post1(url, headers):
    payload = {'chrpos': ['7:105561135', '10:44865737']}
    r = requests.post(url + "/variants/chrpos", data=payload, headers={})
    assert r.status_code == 200 and len(r.json()) == 2


def test_chrpos_post2(url, headers):
    payload = {'chrpos': ['7:105561135', '10:44865737']}
    r = requests.post(url + "/variants/chrpos", data=payload, headers={})
    assert r.status_code == 200 and len(r.json()) == 2


def test_chrpos_post3(url, headers):
    payload = {'chrpos': ['7:105561135', '10:44865737'], 'radius': 100}
    r = requests.post(url + "/variants/chrpos", data=payload, headers={})
    assert r.status_code == 200 and len(r.json()) == 2


@pytest.mark.skip
def test_afl2_get0(url, headers):
    headers = headers.copy()
    del headers['Authorization']
    r = requests.get(url + "/variants/afl2/snplist", headers=headers)
    assert r.status_code == 401


def test_afl2_get1(url, headers):
    r = requests.get(url + "/variants/afl2/snplist", headers={})
    assert r.status_code == 200 and len(r.json()) > 17500


def test_afl2_get2(url, headers):
    r = requests.get(url + "/variants/afl2/rsid/rs234,rs123", headers={})
    assert r.status_code == 200 and len(r.json()) == 2


def test_afl2_get3(url, headers):
    r = requests.get(url + "/variants/afl2/chrpos/7:105561135-105563135,10:44865737", headers={})
    assert r.status_code == 200 and len(r.json()) == 16


@pytest.mark.skip
def test_afl2_post0(url, headers):
    headers = headers.copy()
    del headers['Authorization']
    payload = {'chrpos': ['7:105561135', '10:44865737'], 'rsid': ['rs123']}
    r = requests.post(url + "/variants/afl2", data=payload, headers=headers)
    assert r.status_code == 401


def test_afl2_post1(url, headers):
    payload = {'chrpos': ['7:105561135', '10:44865737'], 'rsid': ['rs123']}
    r = requests.post(url + "/variants/afl2", data=payload, headers={})
    assert r.status_code == 200 and len(r.json()) == 3
