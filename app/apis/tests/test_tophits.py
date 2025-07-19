import requests


# Anonymous
def test_tophits_unauthed(url, headers):
    headers = headers.copy()
    del headers['Authorization']
    payload = {'id': ['ieu-a-2', 'ieu-a-998']}
    r = requests.post(url + "/tophits", data=payload, headers=headers)
    assert r.status_code == 401


# Use preclumped
def test_tophits_preclumped(url, headers):
    payload = {'id': ['ieu-a-2', 'ieu-a-998']}
    r = requests.post(url + "/tophits", data=payload, headers=headers)
    o = r.json()
    assert r.status_code == 200 and 75 < len(o) < 85
    assert set([x.get('id') for x in o]) == {'ieu-a-2'}


# Do not use preclumped, and force clumping again (should give the same results as above)
def test_tophits_rerun_clumping(url, headers):
    payload = {'id': ['ieu-a-2', 'ieu-a-998'], 'preclumped': 0}
    r = requests.post(url + "/tophits", data=payload, headers=headers)
    o = r.json()
    assert r.status_code == 200 and 75 < len(o) < 85
    assert set([x.get('id') for x in o]) == {'ieu-a-2'}


def test_tophits_no_clumping(url, headers):
    payload = {'id': ['ieu-a-2', 'ieu-a-998'], 'preclumped': 0, 'clump': 0}
    r = requests.post(url + "/tophits", data=payload, headers=headers)
    o = r.json()
    assert r.status_code == 200 and len(o) > 2000
    assert set([x.get('id') for x in o]) == {'ieu-a-2'}


# Use preclumped
def test_tophits_preclumped_private(url, headers):
    payload = {'id': ['ieu-a-2', 'ieu-a-998', 'ieu-b-1']}
    r = requests.post(url + "/tophits", data=payload, headers=headers)
    o = r.json()
    assert r.status_code == 200 and 85 < len(o) < 95
    assert set([x.get('id') for x in o]) == {'ieu-a-2', 'ieu-b-1'}


def test_tophits_rerun_clumping_private(url, headers):
    payload = {'id': ['ieu-a-2', 'ieu-a-998', 'ieu-b-1'], 'preclumped': 0}
    r = requests.post(url + "/tophits", data=payload, headers=headers)
    o = r.json()
    assert r.status_code == 200 and 85 < len(o) < 90
    assert set([x.get('id') for x in o]) == {'ieu-a-2', 'ieu-b-1'}


def test_tophits_no_clumping_private(url, headers):
    payload = {'id': ['ieu-a-2', 'ieu-a-998', 'ieu-b-1'], 'preclumped': 0, 'clump': 0}
    r = requests.post(url + "/tophits", data=payload, headers=headers)
    o = r.json()
    assert r.status_code == 200 and len(o) > 2300
    assert set([x.get('id') for x in o]) == {'ieu-a-2', 'ieu-b-1'}


# When PLINK does not generate the .clumped file because there is no clump at all
def test_tophits_no_result(url, headers):
    payload = {'id': ['ukb-d-F5_DEPRESSIO'], 'kb': 5000}
    r = requests.post(url + "/tophits", data=payload, headers=headers)
    assert r.status_code == 200


def test_tophits_rerun_clumping_with_diff_pval(url, headers):
    payload = {'id': ['ebi-a-GCST011081'], 'pval': 0.00005, 'preclumped': 0, 'clump': 1}
    r = requests.post(url + "/tophits", data=payload, headers=headers)
    o = r.json()
    assert r.status_code == 200 and len(o) > 40
