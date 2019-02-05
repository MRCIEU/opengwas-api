import requests


def test_clumping1(url):
    payload = {'rsid': ['rs756190', 'rs7526762', 'rs7601028', 'rs7622475', 'rs9300092', 'rs9309995'],
               'pval': [1.607e-33, 4.813e-15, 1.502e-29, 3.961e-14, 2.246e-08, 9.035e-10]}
    r = requests.post(url + "/ld/clump", data=payload)
    assert r.status_code == 200 and len(r.json()) < 6 and len(r.json()) > 0


def test_clumping2(url):
    payload = {'rsid': ['rs756190', 'rs7526762', 'rs7601028', 'rs7622475', 'rs9300092', 'rs9309995'],
               'pval': [1.607e-33, 4.813e-15, 1.502e-29, 3.961e-14, 2.246e-08, 9.035e-10], 'pthresh': 1e-10}
    r = requests.post(url + "/ld/clump", data=payload)
    assert r.status_code == 200 and len(r.json()) <= 4 and len(r.json()) > 0
