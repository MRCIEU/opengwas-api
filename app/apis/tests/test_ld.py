import requests


def test_clumping0(url, headers):
    headers = headers.copy()
    del headers['Authorization']
    payload = {'rsid': ['rs4988235', 'rs182549'],
               'pval': [5e-10, 5e-9]}
    r = requests.post(url + "/ld/clump", data=payload, headers=headers)
    assert r.status_code == 401


def test_clumping1(url, headers):
    payload = {'rsid': ['rs756190', 'rs7526762', 'rs7601028', 'rs7622475', 'rs9300092', 'rs9309995'],
               'pval': [1.607e-33, 4.813e-15, 1.502e-29, 3.961e-14, 2.246e-08, 9.035e-10]}
    r = requests.post(url + "/ld/clump", data=payload, headers=headers)
    assert r.status_code == 200 and len(r.json()) == 5


def test_clumping2(url, headers):
    payload = {'rsid': ['rs756190', 'rs7526762', 'rs7601028', 'rs7622475', 'rs9300092', 'rs9309995'],
               'pval': [1.607e-33, 4.813e-15, 1.502e-29, 3.961e-14, 2.246e-08, 9.035e-10], 'pthresh': 1e-10}
    r = requests.post(url + "/ld/clump", data=payload, headers=headers)
    assert r.status_code == 200 and len(r.json()) == 4


def test_clumping3(url, headers):
    payload = {'rsid': ['rs4988235', 'rs182549'],
               'pval': [5e-10, 5e-9]}
    r = requests.post(url + "/ld/clump", data=payload, headers=headers)
    assert r.status_code == 200 and len(r.json()) == 1


def test_matrix0(url, headers):
    headers = headers.copy()
    del headers['Authorization']
    payload = {'rsid': ['rs4988235', 'rs182549']}
    r = requests.post(url + "/ld/matrix", data=payload, headers=headers)
    assert r.status_code == 401


def test_matrix1(url, headers):
    payload = {'rsid': ['rs756190', 'rs7526762', 'rs7601028', 'rs7622475', 'rs9300092', 'rs9309995']}
    r = requests.post(url + "/ld/matrix", data=payload, headers=headers)
    o = r.json()
    assert r.status_code == 200
    assert 'snplist' in o and len(o['snplist']) == 6
    assert 'matrix' in o and len(o['matrix']) == 6


def test_matrix2(url, headers):
    payload = {'rsid': ['rs4988235', 'rs182549']}
    r = requests.post(url + "/ld/matrix", data=payload, headers=headers)
    o = r.json()
    assert r.status_code == 200
    assert 'snplist' in o and len(o['snplist']) == 2
    assert 'matrix' in o and len(o['matrix']) == 2


def test_matrix3(url, headers):
    payload = {'rsid': ['FAKESNP', 'FAKESNP2']}
    r = requests.post(url + "/ld/matrix", data=payload, headers=headers)
    o = r.json()
    assert r.status_code == 200
    assert 'snplist' in o and len(o['snplist']) == 0
    assert 'matrix' in o and len(o['matrix']) == 0


def test_ref_lookup0(url, headers):
    headers = headers.copy()
    del headers['Authorization']
    payload = {'rsid': ['rs234']}
    r = requests.post(url + "/ld/reflookup", data=payload, headers=headers)
    assert r.status_code == 401


def test_ref_lookup1(url, headers):
    payload = {'rsid': ['rs234']}
    r = requests.post(url + "/ld/reflookup", data=payload, headers=headers)
    o = r.json()
    assert r.status_code == 200 and len(o) == 1
    assert o[0] == 'rs234'


def test_ref_lookup2(url, headers):
    payload = {'rsid': ['rs234', 'fakesnp']}
    r = requests.post(url + "/ld/reflookup", data=payload, headers=headers)
    o = r.json()
    assert r.status_code == 200 and len(o) == 1
    assert o[0] == 'rs234'


def test_ref_lookup3(url, headers):
    payload = {'rsid': ['fakesnp']}
    r = requests.post(url + "/ld/reflookup", data=payload, headers=headers)
    assert r.status_code == 200 and len(r.json()) == 0


def test_ref_lookup4(url, headers):
    payload = {'rsid': ['rs234', 'fakesnp'], 'pop': 'AFR'}
    r = requests.post(url + "/ld/reflookup", data=payload, headers=headers)
    o = r.json()
    assert r.status_code == 200 and len(o) == 1
    assert o[0] == 'rs234'
