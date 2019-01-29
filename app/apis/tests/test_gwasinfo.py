import requests
from apis.tests.token import get_mrbase_access_token
import os

token = get_mrbase_access_token()


# Should return json entries for each study
def test_gwasinfo1(url):
    payload = {'id': [2, 7]}
    r = requests.post(url + "/gwasinfo", data=payload)
    assert r.status_code == 200 and len(r.json()) == 2


# Should return json entries for each study
def test_gwasinfo2(url):
    headers = {'X-API-TOKEN': 'NULL'}
    payload = {'id': [2, 7]}
    r = requests.post(url + "/gwasinfo", data=payload, headers=headers)
    assert r.status_code == 200 and len(r.json()) == 2


### do not have permission to test ###
# Don't get private studies without authentication
def test_gwasinfo3(url):
    headers = {'X-API-TOKEN': 'NULL'}
    payload = {'id': [2, 7, 987]}
    r = requests.post(url + "/gwasinfo", data=payload, headers=headers)
    assert r.status_code == 200 and len(r.json()) == 2


### do not have permission to test ###
# This time should have authentication to get private study
def test_gwasinfo4(url):
    headers = {'X-API-TOKEN': token}
    payload = {'id': [2, 7, 987]}
    r = requests.post(url + "/gwasinfo", data=payload, headers=headers)
    assert r.status_code == 200 and len(r.json()) == 3


# This time should have authentication to get private study
def test_gwasinfo5(url):
    headers = {'X-API-TOKEN': token}
    payload = {}
    r = requests.post(url + "/gwasinfo", data=payload, headers=headers)
    assert r.status_code == 200 and len(r.json()) > 1000


# Using GET
def test_gwasinfo6(url):
    r = requests.get(url + "/gwasinfo")
    assert r.status_code == 200 and len(r.json()) > 1000


# Using GET
def test_gwasinfo7(url):
    r = requests.get(url + "/gwasinfo/2")
    assert r.status_code == 200 and len(r.json()) == 1


# Using GET
def test_gwasinfo8(url):
    r = requests.get(url + "/gwasinfo/2,987")
    assert r.status_code == 200 and len(r.json()) == 1


def test_gwasinfo_add_delete(url):
    payload = {
        'pmid': 1234, 'year': 2010,
        'filename': 'test',
        'path': '/projects/test/test', 'mr': 1,
        'note': 'test',
        'trait': 'Hip circumference', 'category': 'Risk factor', 'subcategory': 'Anthropometric',
        'population': 'European',
        'sex': 'Males', 'ncase': None, 'ncontrol': None, 'sample_size': 60586, 'nsnp': 2725796,
        'unit': 'SD (cm)', 'gid': 1,
        'sd': 8.4548, 'priority': 15, 'author': 'Randall JC', 'consortium': 'GIANT', 'access': 'public'
    }
    headers = {'X-API-TOKEN': token}

    # add record
    r = requests.post(url + "/gwasinfo/add", data=payload, headers=headers)
    uid = str(r.json()['id'])
    assert r.status_code == 200 and isinstance(int(uid), int)

    # delete record
    payload = {'id': uid}
    r = requests.delete(url + "/gwasinfo/delete", data=payload, headers=headers)
    assert r.status_code == 200

    # check deleted
    payload = {'id': [uid]}
    r = requests.post(url + "/gwasinfo", data=payload)
    assert r.status_code == 200 and len(r.json()) == 0


def test_gwasinfo_upload_plain_text(url):
    payload = {
        'pmid': 1234, 'year': 2010,
        'filename': 'test',
        'path': '/projects/test/test', 'mr': 1,
        'note': 'test',
        'trait': 'Hip circumference', 'category': 'Risk factor', 'subcategory': 'Anthropometric',
        'population': 'European',
        'sex': 'Males', 'ncase': None, 'ncontrol': None, 'sample_size': 60586, 'nsnp': 2725796,
        'unit': 'SD (cm)', 'gid': 1,
        'sd': 8.4548, 'priority': 15, 'author': 'Randall JC', 'consortium': 'GIANT', 'access': 'public'
    }
    headers = {'X-API-TOKEN': token}

    # make new metadata
    r = requests.post(url + "/gwasinfo/add", data=payload, headers=headers)
    assert r.status_code == 200
    uid = str(r.json()['id'])
    assert isinstance(int(uid), int)

    file_path = os.path.join('apis', 'tests', 'data', 'jointGwasMc_LDL.head.txt')

    # upload file for this study
    r = requests.post(url + "/gwasinfo/upload", data={
        'id': uid,
        'chr_col': 0,
        'pos_col': 1,
        'snp_col': 2,
        'ea_col': 3,
        'oa_col': 4,
        'eaf_col': 9,
        'beta_col': 5,
        'se_col': 6,
        'pval_col': 8,
        'ncontrol_col': 7,
        'delimiter': 'tab',
        'header': 'True',
        'gzipped': 'False'
    }, files={'gwas_file': open(file_path, 'rb')}, headers=headers)

    assert r.status_code == 201

    # delete metadata
    payload = {'id': uid}
    r = requests.delete(url + "/gwasinfo/delete", data=payload, headers=headers)
    assert r.status_code == 200

def test_gwasinfo_upload_gzip(url):
    payload = {
        'pmid': 1234, 'year': 2010,
        'filename': 'test',
        'path': '/projects/test/test', 'mr': 1,
        'note': 'test',
        'trait': 'Hip circumference', 'category': 'Risk factor', 'subcategory': 'Anthropometric',
        'population': 'European',
        'sex': 'Males', 'ncase': None, 'ncontrol': None, 'sample_size': 60586, 'nsnp': 2725796,
        'unit': 'SD (cm)', 'gid': 1,
        'sd': 8.4548, 'priority': 15, 'author': 'Randall JC', 'consortium': 'GIANT', 'access': 'public'
    }
    headers = {'X-API-TOKEN': token}

    # make new metadata
    r = requests.post(url + "/gwasinfo/add", data=payload, headers=headers)
    assert r.status_code == 200
    uid = str(r.json()['id'])
    assert isinstance(int(uid), int)

    file_path = os.path.join('apis', 'tests', 'data', 'jointGwasMc_LDL.head.txt.gz')

    # upload file for this study
    r = requests.post(url + "/gwasinfo/upload", data={
        'id': uid,
        'chr_col': 0,
        'pos_col': 1,
        'snp_col': 2,
        'ea_col': 3,
        'oa_col': 4,
        'eaf_col': 9,
        'beta_col': 5,
        'se_col': 6,
        'pval_col': 8,
        'ncontrol_col': 7,
        'delimiter': 'tab',
        'header': 'True',
        'gzipped': 'True'
    }, files={'gwas_file': open(file_path, 'rb')}, headers=headers)

    assert r.status_code == 201

    # delete metadata
    payload = {'id': uid}
    r = requests.delete(url + "/gwasinfo/delete", data=payload, headers=headers)
    assert r.status_code == 200