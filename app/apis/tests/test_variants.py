import requests


## GET

def test_rsid_get1(url):
    r = requests.get(url + "/variants/rsid/rs234")
    assert r.status_code == 200 and len(r.json()) == 1


def test_rsid_get2(url):
    r = requests.get(url + "/variants/rsid/rs234,rs333")
    assert r.status_code == 200 and len(r.json()) == 2


def test_chrpos_get1(url):
    r = requests.get(url + "/variants/chrpos/7:105561135")
    assert r.status_code == 200 and len(r.json()) == 1


def test_chrpos_get2(url):
    r = requests.get(url + "/variants/chrpos/7:105561135?radius=1000")
    assert r.status_code == 200 and len(r.json()[0]) > 1


def test_gene_get1(url):
    r = requests.get(url + "/variants/gene/ENSG00000123374")
    assert r.status_code == 200 and len(r.json()) > 1


# ## POST


def test_rsid_post1(url):
    payload = {'rsid': ['rs234', 'rs333']}
    r = requests.post(url + "/variants/rsid", data=payload)
    assert r.status_code == 200 and len(r.json()) == 2


def test_chrpos_post1(url):
    payload = {'chrpos': ['7:105561135', '10:44865737']}
    r = requests.post(url + "/variants/chrpos", data=payload)
    assert r.status_code == 200 and len(r.json()) == 2


def test_chrpos_post2(url):
    payload = {'chrpos': ['7:105561135', '10:44865737']}
    r = requests.post(url + "/variants/chrpos", data=payload)
    assert r.status_code == 200 and len(r.json()) == 2


def test_chrpos_post3(url):
    payload = {'chrpos': ['7:105561135', '10:44865737'], 'radius': 100}
    r = requests.post(url + "/variants/chrpos", data=payload)
    assert r.status_code == 200 and len(r.json()) == 2
