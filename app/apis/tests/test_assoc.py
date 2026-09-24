import pytest
import requests


# # Anonymous
# def test_assoc_get0(url, headers):
#     headers = headers.copy()
#     del headers['Authorization']
#     r = requests.get(url + "/associations/ieu-a-2/rs234", headers=headers)
#     assert r.status_code == 401
#
#
# def test_assoc_get1(url, headers):
#     r = requests.get(url + "/associations/ieu-a-2/rs234", headers=headers)
#     assert r.status_code == 200 and len(r.json()) == 1
#
#
# def test_assoc_get2(url, headers):
#     r = requests.get(url + "/associations/ieu-a-300/rs4988235", headers=headers)
#     assert r.status_code == 200 and len(r.json()) == 1
#
#
# # No result for ieu-a-998 because it's in the 'developer' group
# def test_assoc_get3(url, headers):
#     r = requests.get(url + "/associations/ieu-a-2,ieu-a-998/rs234", headers=headers)
#     assert r.status_code == 200 and len(r.json()) == 1
#
#
# # No result for ieu-a-998 because it's in the 'developer' group
# def test_assoc_get4(url, headers):
#     r = requests.get(url + "/associations/ieu-a-2,ieu-a-7,ieu-a-998/rs234", headers=headers)
#     assert r.status_code == 200 and len(r.json()) == 2
#
#
# # No result for ieu-a-998 because it's in the 'developer' group
# def test_assoc_get5(url, headers):
#     r = requests.get(url + "/associations/ieu-a-2,ieu-a-7,ieu-a-998/rs234,rs123", headers=headers)
#     assert r.status_code == 200 and len(r.json()) == 4
#
#
# # ieu-b-5008 is in the 'biogen' group, of which the test user is a member
# def test_assoc_get6(url, headers):
#     r = requests.get(url + "/associations/ieu-a-2,ieu-a-7,ieu-b-5008/rs234,rs123", headers=headers)
#     assert r.status_code == 200 and len(r.json()) == 6


def test_assoc_unauthed(url):
    payload = {'id': ['ieu-a-2', 'ieu-a-7', 'ieu-a-998'], 'variant': ['rs234', 'rs123']}
    r = requests.post(url + "/associations", data=payload)
    assert r.status_code == 401


## TODO: Find a public, non-commercial dataset
# def test_non_commercial_without_approval(url, headers):
#     payload = {'id': [''], 'variant': ['rs234']}
#     r = requests.post(url + "/associations", data=payload, headers=headers)
#     assert r.status_code == 200 and len(r.json()) == 0


# No result for ieu-a-998 because it's in the 'developer' group
def test_assoc_private_no_access(url, headers):
    payload = {'id': ['ieu-a-2', 'ieu-a-7', 'ieu-a-998'], 'variant': ['rs234', 'rs123']}
    r = requests.post(url + "/associations", data=payload, headers=headers)
    assert r.status_code == 200 and len(r.json()) == 4


# ieu-b-5008 is in the 'biogen' group, of which the test user is a member
def test_assoc_private_has_access(url, headers):
    payload = {'id': ['ieu-a-2', 'ieu-a-7', 'ieu-b-5008'], 'variant': ['rs234', 'rs123']}
    r = requests.post(url + "/associations", data=payload, headers=headers)
    assert r.status_code == 200 and len(r.json()) == 6


def test_assoc_unavail_rsid(url, headers):
    payload = {'id': ['ieu-a-1', 'ieu-a-2'], 'variant': ['rs6689306']}
    r = requests.post(url + "/associations", data=payload, headers=headers)
    assert r.status_code == 200 and len(r.json()) == 0


def test_assoc_proxies(url, headers):
    payload = {'id': ['ieu-a-1', 'ieu-a-2'], 'variant': ['rs6689306'], 'proxies': 1}
    r = requests.post(url + "/associations", data=payload, headers=headers)
    assert r.status_code == 200 and len(r.json()) == 2


def test_assoc_unavail_rsid_2(url, headers):
    payload = {'id': ['ieu-a-1', 'ieu-a-2'], 'variant': ['rs234', 'rs123', 'rs6689306']}
    r = requests.post(url + "/associations", data=payload, headers=headers)
    assert r.status_code == 200 and len(r.json()) == 4


def test_assoc_proxies_2(url, headers):
    payload = {'id': ['ieu-a-1', 'ieu-a-2'], 'variant': ['rs234', 'rs123', 'rs6689306'], 'proxies': 1}
    r = requests.post(url + "/associations", data=payload, headers=headers)
    assert r.status_code == 200 and len(r.json()) == 6


# This snp has 1500+ proxies
def test_assoc_proxies_3(url, headers):
    payload = {'id': ['ieu-a-2'], 'variant': ['rs58879558'], 'proxies': 1}
    r = requests.post(url + "/associations", data=payload, headers=headers)
    assert r.status_code == 200 and len(r.json()) == 1


# ukb-e datasets used to have beta and eaf flipped by fix_legacy_value_errors().
# rs6567160 C is the BMI-raising MC4R allele with frequency ~0.3 in South Asians.
@pytest.mark.parametrize('x_api_source', ['R/TwoSampleMR', 'ieugwasr/1.1.0', 'ieugwasr/1.1.0;TwoSampleMR/0.7.9'])
def test_assoc_ukb_e_values(url, headers, x_api_source):
    payload = {'id': ['ukb-e-23104_CSA'], 'variant': ['rs6567160'], 'proxies': 0}
    r = requests.post(url + "/associations", data=payload, headers={**headers, 'X-API-SOURCE': x_api_source})
    assert r.status_code == 200 and len(r.json()) == 1
    a = r.json()[0]
    assert a['ea'] == 'C' and a['beta'] > 0 and a['eaf'] < 0.5


def test_assoc_rsid(url, headers):
    payload = {'id': ['ieu-b-2'], 'variant': ['rs234']}
    r = requests.post(url + "/associations", data=payload, headers=headers)
    assert r.status_code == 200 and len(r.json()) == 1


def test_assoc_chrpos(url, headers):
    payload = {'id': ['ieu-a-2'], 'variant': ['7:105561135'], 'proxies': 0}
    r1 = requests.post(url + "/associations", data=payload, headers=headers)
    assert r1.status_code == 200
    payload = {'id': ['ieu-a-2'], 'variant': ['rs234'], 'proxies': 0}
    r2 = requests.post(url + "/associations", data=payload, headers=headers)
    assert r2.status_code == 200
    assert r1.json()[0]['rsid'] == r2.json()[0]['rsid']


def test_assoc_rsid_chrpos(url, headers):
    payload = {'id': ['ieu-a-2'], 'variant': ['7:105561135', 'rs1205'], 'proxies': 0}
    r1 = requests.post(url + "/associations", data=payload, headers=headers)
    assert r1.status_code == 200 and len(r1.json()) == 2
    assert 'rs234' in [x['rsid'] for x in r1.json()]


def test_assoc_rsid_cprange(url, headers):
    payload = {'id': ['ieu-a-2'], 'variant': ['7:105561135-105571135', 'rs1205'], 'proxies': 0}
    r1 = requests.post(url + "/associations", data=payload, headers=headers)
    assert r1.status_code == 200 and len(r1.json()) == 9
    assert 'rs1205' in [x['rsid'] for x in r1.json()]


def test_assoc_cprange(url, headers):
    payload = {'id': ['ieu-a-300'], 'variant': ['1:109724880-109904880'], 'proxies': 0}
    r1 = requests.post(url + "/associations", data=payload, headers=headers)
    assert r1.status_code == 200 and len(r1.json()) > 200


# @pytest.mark.skip
# def test_assoc_chunked_post0(url):
#     payload = {'id': ['ieu-a-2', 'ieu-a-7', 'ieu-a-998'], 'variant': ['rs234', 'rs123']}
#     r = requests.post(url + "/associations/chunked", data=payload)
#     assert r.status_code == 401
#
#
# @pytest.mark.skip
# def test_assoc_chunked_post1(url, headers):
#     payload = {'id': ['ieu-a-2', 'ieu-a-7', 'ieu-a-998'], 'variant': ['rs234', 'rs123']}
#     r = requests.post(url + "/associations/chunked", data=payload, headers=headers)
#     assert r.status_code == 200 and len(r.json()) == 4
#
#
# @pytest.mark.skip
# def test_assoc_chunked_post2(url, headers):
#     payload = {'id': ['ieu-a-2', 'ieu-a-7', 'ieu-b-5008'], 'variant': ['rs234', 'rs123']}
#     r = requests.post(url + "/associations/chunked", data=payload, headers=headers)
#     assert r.status_code == 200 and len(r.json()) == 6
#
#
# @pytest.mark.skip
# def test_assoc_chunked_post3(url, headers):
#     payload = {'id': ['ieu-a-1', 'ieu-a-2'], 'variant': ['rs6689306']}
#     r = requests.post(url + "/associations/chunked", data=payload, headers=headers)
#     assert r.status_code == 200 and len(r.json()) == 0
#
#
# @pytest.mark.skip
# def test_assoc_chunked_post4(url, headers):
#     payload = {'id': ['ieu-a-1', 'ieu-a-2'], 'variant': ['rs6689306'], 'proxies': 1}
#     r = requests.post(url + "/associations/chunked", data=payload, headers=headers)
#     assert r.status_code == 200 and len(r.json()) == 2
#
#
# @pytest.mark.skip
# def test_assoc_chunked_post5(url, headers):
#     payload = {'id': ['ieu-a-1', 'ieu-a-2'], 'variant': ['rs234', 'rs123', 'rs6689306']}
#     r = requests.post(url + "/associations/chunked", data=payload, headers=headers)
#     assert r.status_code == 200 and len(r.json()) == 4
#
#
# @pytest.mark.skip
# def test_assoc_chunked_post6(url, headers):
#     payload = {'id': ['ieu-a-1', 'ieu-a-2'], 'variant': ['rs234', 'rs123', 'rs6689306'], 'proxies': 1}
#     r = requests.post(url + "/associations/chunked", data=payload, headers=headers)
#     assert r.status_code == 200 and len(r.json()) == 6
#
#
# @pytest.mark.skip
# def test_chunked_chrpos1(url, headers):
#     payload = {'id': ['ieu-a-2'], 'variant': ['7:105561135'], 'proxies': 0}
#     r1 = requests.post(url + "/associations/chunked", data=payload, headers=headers)
#     assert r1.status_code == 200
#     payload = {'id': ['ieu-a-2'], 'variant': ['rs234'], 'proxies': 0}
#     r2 = requests.post(url + "/associations/chunked", data=payload, headers=headers)
#     assert r2.status_code == 200
#     assert r1.json()[0]['rsid'] == r2.json()[0]['rsid']
#
#
# @pytest.mark.skip
# def test_chunked_chrpos2(url, headers):
#     payload = {'id': ['ieu-a-2'], 'variant': ['7:105561135', 'rs1205'], 'proxies': 0}
#     r1 = requests.post(url + "/associations/chunked", data=payload, headers=headers)
#     assert r1.status_code == 200 and len(r1.json()) == 2
#     assert 'rs234' in [x['rsid'] for x in r1.json()]
#
#
# @pytest.mark.skip
# def test_chunked_chrpos3(url, headers):
#     payload = {'id': ['ieu-a-2'], 'variant': ['7:105561135-105571135', 'rs1205'], 'proxies': 0}
#     r1 = requests.post(url + "/associations/chunked", data=payload, headers=headers)
#     assert r1.status_code == 200 and len(r1.json()) == 9
#     assert 'rs1205' in [x['rsid'] for x in r1.json()]
