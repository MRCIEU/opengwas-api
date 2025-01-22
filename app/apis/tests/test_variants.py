from collections import defaultdict
import requests


# # Anonymous
# def test_rsid_get0(url, headers):
#     headers = headers.copy()
#     del headers['Authorization']
#     r = requests.get(url + "/variants/rsid/rs234", headers=headers)
#     assert r.status_code == 401
#
#
# def test_rsid_get1(url, headers):
#     r = requests.get(url + "/variants/rsid/rs234", headers=headers)
#     assert r.status_code == 200 and len(r.json()) == 1
#
#
# def test_rsid_get2(url, headers):
#     r = requests.get(url + "/variants/rsid/rs234,rs333", headers=headers)
#     assert r.status_code == 200 and len(r.json()) == 2


# def test_chrpos_get0(url, headers):
#     headers = headers.copy()
#     del headers['Authorization']
#     r = requests.get(url + "/variants/chrpos/7:105561135", headers=headers)
#     assert r.status_code == 401
#
#
# def test_chrpos_get1(url, headers):
#     r = requests.get(url + "/variants/chrpos/7:105561135", headers=headers)
#     assert r.status_code == 200 and len(r.json()) == 1
#
#
# def test_chrpos_get2(url, headers):
#     r = requests.get(url + "/variants/chrpos/7:105561135?radius=1000", headers=headers)
#     assert r.status_code == 200 and len(r.json()[0]) > 1
#
#
# def test_chrpos_get3(url, headers):
#     r = requests.get(url + "/variants/chrpos/7:105561135-105563135,10:44865737", headers=headers)
#     o = r.json()
#     assert r.status_code == 200 and len(o) == 2
#     assert len(o[0]) >= 12 or len(o[1]) >= 12


def test_gene_get0(url, headers):
    headers = headers.copy()
    del headers['Authorization']
    r = requests.get(url + "/variants/gene/ENSG00000123374", headers=headers)
    assert r.status_code == 401


def test_gene_get1(url, headers):
    r = requests.get(url + "/variants/gene/ENSG00000123374", headers=headers)
    assert r.status_code == 200 and len(r.json()) > 2800


# https://github.com/MRCIEU/opengwas-api/issues/16
def test_gene_get2(url, headers):
    r = requests.get(url + "/variants/gene/ENSG00000111684", headers=headers)
    assert r.status_code == 200 and len(r.json()) > 15900


def test_rsid_post0(url, headers):
    headers = headers.copy()
    del headers['Authorization']
    payload = {'rsid': ['rs234', 'rs333']}
    r = requests.post(url + "/variants/rsid", data=payload, headers=headers)
    assert r.status_code == 401


def test_rsid_post1(url, headers):
    payload = {'rsid': ['rs234', 'rs333']}
    r = requests.post(url + "/variants/rsid", data=payload, headers=headers)
    assert r.status_code == 200
    assert set([s['_id'] for s in r.json()]) == {'rs234', 'rs333'}


def test_chrpos_post1(url, headers):
    payload = {'chrpos': ['7:105561135', '10:44865737']}
    r = requests.post(url + "/variants/chrpos", data=payload, headers=headers)
    assert r.status_code == 200
    assert set([s['ID'] for s in r.json()]) == {'rs234', 'rs60507664', 'rs386565244', 'rs17358109', 'rs7777'}


def test_chrpos_post2(url, headers):
    payload = {'chrpos': ['7:105561000-105561050', '10:44865737']}
    r = requests.post(url + "/variants/chrpos", data=payload, headers=headers)
    assert r.status_code == 200
    snps = r.json()
    assert len(snps) == 23
    assert len([s for s in snps if s['CHROM'] == '7']) == 22
    assert [s['ID'] for s in snps if s['CHROM'] == '10'] == ['rs7777']


def test_chrpos_post3(url, headers):
    payload = {'chrpos': ['7:105561000-105561050', '10:44865737'], 'radius': 10}
    r = requests.post(url + "/variants/chrpos", data=payload, headers=headers)
    assert r.status_code == 200
    rsids_by_chr = defaultdict(set)
    snps = r.json()
    assert len(snps) == 46
    for s in snps:
        rsids_by_chr[s['CHROM']].add(s['ID'])
    assert len(rsids_by_chr['7']) == 32
    assert len(rsids_by_chr['10']) == 14
    # Check for boundaries 7:105560988 and 7:105561063
    assert 'rs1218382318' not in rsids_by_chr['7'] and 'rs901986410' not in rsids_by_chr['7']
    # Check for boundaries 10:44865726 and 10:44865741
    assert 'rs534236011' not in rsids_by_chr['10'] and 'rs1241896820' not in rsids_by_chr['10']


def test_afl2_get0(url, headers):
    headers = headers.copy()
    del headers['Authorization']
    r = requests.get(url + "/variants/afl2/snplist", headers=headers)
    assert r.status_code == 401


def test_afl2_get1(url, headers):
    r = requests.get(url + "/variants/afl2/snplist", headers=headers)
    assert r.status_code == 200 and len(r.json()) > 17500


# def test_afl2_get2(url, headers):
#     r = requests.get(url + "/variants/afl2/rsid/rs234,rs123", headers=headers)
#     assert r.status_code == 200 and len(r.json()) == 2
#
#
# def test_afl2_get3(url, headers):
#     r = requests.get(url + "/variants/afl2/chrpos/7:105561135-105563135,10:44865737", headers=headers)
#     assert r.status_code == 200 and len(r.json()) == 16


def test_afl2_post0(url, headers):
    headers = headers.copy()
    del headers['Authorization']
    payload = {'chrpos': ['7:105561135', '10:44865737'], 'rsid': ['rs123']}
    r = requests.post(url + "/variants/afl2", data=payload, headers=headers)
    assert r.status_code == 401


def test_afl2_post1(url, headers):
    payload = {'chrpos': ['7:105561135', '10:44865737'], 'rsid': ['rs123']}
    r = requests.post(url + "/variants/afl2", data=payload, headers=headers)
    assert r.status_code == 200 and len(r.json()) == 3
