import requests


def test_clumping1(url):
    payload = {'rsid': ['rs756190', 'rs7526762', 'rs7601028', 'rs7622475', 'rs9300092', 'rs9309995'],
               'pval': [1.607e-33, 4.813e-15, 1.502e-29, 3.961e-14, 2.246e-08, 9.035e-10]}
    r = requests.post(url + "/ld/clump", data=payload)
    assert r.status_code == 200
    assert len(r.json()) < 6
    assert len(r.json()) > 0


def test_clumping2(url):
    payload = {'rsid': ['rs756190', 'rs7526762', 'rs7601028', 'rs7622475', 'rs9300092', 'rs9309995'],
               'pval': [1.607e-33, 4.813e-15, 1.502e-29, 3.961e-14, 2.246e-08, 9.035e-10], 'pthresh': 1e-10}
    r = requests.post(url + "/ld/clump", data=payload)
    assert r.status_code == 200
    assert len(r.json()) <= 4
    assert len(r.json()) > 0


def test_clumping3(url):
    payload = {'rsid': ['rs4988235', 'rs182549'],
               'pval': [5e-10, 5e-9]}
    r = requests.post(url + "/ld/clump", data=payload)
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_matrix1(url):
    payload = {'rsid': ['rs756190', 'rs7526762', 'rs7601028', 'rs7622475', 'rs9300092', 'rs9309995']}
    r = requests.post(url + "/ld/matrix", data=payload)
    o = r.json()
    assert r.status_code == 200
    assert 'snplist' in o
    assert 'matrix' in o
    assert len(o['snplist']) == len(o['matrix'])


def test_matrix2(url):
    payload = {'rsid': ['rs4988235', 'rs182549']}
    r = requests.post(url + "/ld/matrix", data=payload)
    o = r.json()
    assert r.status_code == 200
    assert 'snplist' in o
    assert 'matrix' in o
    assert len(o['snplist']) == len(o['matrix'])


def test_matrix3(url):
    payload = {'rsid': ['FAKESNP', 'FAKESNP2']}
    r = requests.post(url + "/ld/matrix", data=payload)
    o = r.json()
    assert r.status_code == 200
    assert 'snplist' in o
    assert 'matrix' in o
    assert len(o['snplist']) == len(o['matrix'])
