import requests
from apis.tests.token import get_mrbase_access_token
import os
import shutil
import tempfile

token = get_mrbase_access_token()


def test_gwasinfo_add_delete(url):
    payload = {
        'pmid': 1234, 
        'year': 2010, 
        'mr': 1,
        'note': 'test',
        'build': 'HG19/GRCh37',
        'trait': 'Hip circumference', 'category': 'Risk factor', 'subcategory': 'Anthropometric',
        'population': 'European',
        'sex': 'Males', 
        'ncase': None, 
        'ncontrol': None, 
        'sample_size': 60586, 
        'nsnp': 2725796,
        'unit': 'SD (cm)', 
        'group_name': "public",
        'sd': 8.4548, 
        'priority': 15, 
        'author': 'Randall JC', 
        'consortium': 'GIANT'
    }
    headers = {'X-API-TOKEN': token}

    # add record
    r = requests.post(url + "/edit/add", data=payload, headers=headers)
    print(r.json())
    uid = str(r.json()['id'])
    assert r.status_code == 200 and isinstance(int(uid.replace('IEU-b-', '')), int)

    # check present
    r = requests.get(url + "/edit/check/" + uid, headers=headers)
    assert r.status_code == 200 and len(r.json()) == 1

    # delete record
    r = requests.delete(url + "/edit/delete/" + uid, headers=headers)
    assert r.status_code == 200

    # check deleted
    payload = {'id': [uid]}
    r = requests.get(url + "/edit/check/" + uid, headers=headers)
    assert r.status_code == 200 and len(r.json()) == 0

    # check not deleted everything else
    payload = {'id': ["ieu-a-2"]}
    r = requests.post(url + "/gwasinfo", data=payload)
    assert r.status_code == 200 and len(r.json()) == 1


def test_gwasinfo_upload_plain_text(url):
    payload = {
        'pmid': 1234,
        'year': 2010,
        'mr': 1,
        'note': 'test',
        'build': 'HG19/GRCh37',
        'trait': 'Hip circumference', 'category': 'Risk factor', 'subcategory': 'Anthropometric',
        'population': 'European',
        'sex': 'Males', 
        'ncase': None, 
        'ncontrol': None, 
        'sample_size': 60586, 
        'nsnp': 2725796,
        'unit': 'SD (cm)', 
        'group_name': "public",
        'sd': 8.4548, 
        'priority': 15, 
        'author': 'Randall JC', 
        'consortium': 'GIANT'
    }
    headers = {'X-API-TOKEN': token}

    # make new metadata
    r = requests.post(url + "/edit/add", data=payload, headers=headers)
    assert r.status_code == 200
    uid = str(r.json()['id'])
    assert isinstance(int(uid.replace('IEU-b-', '')), int)

    file_path = os.path.join('apis', 'tests', 'data', 'jointGwasMc_LDL.head.txt')

    # upload file for this study
    r = requests.post(url + "/edit/upload", data={
        'id': uid,
        'chr_col': 1,
        'pos_col': 2,
        'snp_col': 3,
        'ea_col': 4,
        'oa_col': 5,
        'eaf_col': 10,
        'beta_col': 6,
        'se_col': 7,
        'pval_col': 9,
        'ncontrol_col': 8,
        'delimiter': 'tab',
        'header': 'True',
        'gzipped': 'False'
    }, files={'gwas_file': open(file_path, 'rb')}, headers=headers)

    assert r.status_code == 201


def test_gwasinfo_upload_gzip(url):
    payload = {
        'pmid': 1234, 
        'year': 2010, 
        'mr': 1,
        'note': 'test',
        'build': 'HG19/GRCh37',
        'trait': 'Hip circumference', 
        'category': 'Risk factor', 'subcategory': 'Anthropometric',
        'population': 'European',
        'sex': 'Males', 
        'ncase': None, 
        'ncontrol': None, 
        'sample_size': 60586, 
        'nsnp': 2725796,
        'unit': 'SD (cm)', 
        'group_name': "public",
        'sd': 8.4548, 
        'priority': 15, 
        'author': 'Randall JC', 
        'consortium': 'GIANT'
    }
    headers = {'X-API-TOKEN': token}

    # make new metadata
    r = requests.post(url + "/edit/add", data=payload, headers=headers)
    assert r.status_code == 200
    uid = str(r.json()['id'])
    assert isinstance(int(uid.replace('IEU-b-', '')), int)

    file_path = os.path.join('apis', 'tests', 'data', 'jointGwasMc_LDL.head.txt.gz')

    # upload file for this study
    r = requests.post(url + "/edit/upload", data={
        'id': uid,
        'chr_col': 1,
        'pos_col': 2,
        'snp_col': 3,
        'ea_col': 4,
        'oa_col': 5,
        'eaf_col': 10,
        'beta_col': 6,
        'se_col': 7,
        'pval_col': 9,
        'ncontrol_col': 8,
        'delimiter': 'tab',
        'header': 'True',
        'gzipped': 'True'
    }, files={'gwas_file': open(file_path, 'rb')}, headers=headers)

    assert r.status_code == 201


def test_gwasinfo_upload_large(url):
    file_url = 'https://zenodo.org/record/1251813/files/bmi.giant-ukbb.meta-analysis.combined.23May2018.txt.gz?download=1'

    payload = {
        'pmid': 1234, 
        'year': 2010, 
        'mr': 1,
        'note': 'test',
        'build': 'HG19/GRCh37',
        'trait': 'BMI', 'category': 'Risk factor', 'subcategory': 'Anthropometric',
        'population': 'European',
        'sex': 'Males', 
        'ncase': None, 
        'ncontrol': None, 
        'sample_size': 60586, 
        'nsnp': 2725796,
        'unit': 'SD (cm)', 
        'group_name': "public",
        'sd': 8.4548, 
        'priority': 15, 
        'author': 'Randall JC', 
        'consortium': 'GIANT'
    }
    headers = {'X-API-TOKEN': token}

    # make new metadata
    r = requests.post(url + "/edit/add", data=payload, headers=headers)
    assert r.status_code == 200
    uid = str(r.json()['id'])
    assert isinstance(int(uid.replace('IEU-b-', '')), int)

    # make tmp file
    tmp = tempfile.NamedTemporaryFile()
    assert os.path.isfile(tmp.name)

    # save downloaded file to tmp
    with open(tmp.name, 'bw') as f:
        with requests.get(file_url, stream=True, allow_redirects=True) as r:
            shutil.copyfileobj(r.raw, f)

    # upload file for this study
    r = requests.post(url + "/edit/upload", data={
        'id': uid,
        'chr_col': 1,
        'pos_col': 2,
        'snp_col': 3,
        'ea_col': 4,
        'oa_col': 5,
        'eaf_col': 6,
        'beta_col': 7,
        'se_col': 8,
        'pval_col': 9,
        'ncontrol_col': 10,
        'delimiter': 'space',
        'header': 'True',
        'gzipped': 'True'
    }, files={'gwas_file': open(tmp.name, 'rb')}, headers=headers)

    assert r.status_code == 201

    # delete GWAS file
    tmp.close()
    assert not os.path.isfile(tmp.name)
