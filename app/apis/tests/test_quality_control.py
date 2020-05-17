import requests
from apis.tests.token import get_mrbase_access_token
import os
from pathlib import Path
from resources.globals import Globals

token = get_mrbase_access_token()


def test_release(url):
    headers = {'X-API-TOKEN': token}

    data = {
        'pmid': 1234, 'year': 2010, 'mr': 1,
        'note': 'test',
        'trait': 'Hip circumference', 'category': 'Risk factor', 'subcategory': 'Anthropometric',
        'population': 'European',
        'sex': 'Males', 'ncase': None, 'ncontrol': None, 'sample_size': 60586, 'nsnp': 2725796,
        'unit': 'SD (cm)', 'group_name': "developer", "build": 'HG19/GRCh37',
        'sd': 8.4548, 'priority': 15, 'author': 'Randall JC', 'consortium': 'GIANT'
    }

    # make new metadata
    r = requests.post(url + "/edit/add", data=data, headers=headers)
    assert r.status_code == 200
    uid = str(r.json()['id'])
    assert isinstance(int(uid.replace('ieu-b-', '')), int)

    # define gwas summary stats file
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

    # set quality control
    payload = {'id': uid, 'comments': "test", 'passed_qc': "True"}
    r = requests.post(url + '/quality_control/release', data=payload, headers=headers)
    assert r.status_code == 200

    # delete quality control (permission denied)
    payload = {'id': uid}
    r = requests.delete(url + "/quality_control/delete", data=payload, headers={'X-API-TOKEN': 'null'})
    assert r.status_code == 403

    # check html report
    html_report = uid + "_report.html"
    study_folder = os.path.join(Globals.UPLOAD_FOLDER, uid)
    Path(os.path.join(study_folder, html_report)).touch()
    r = requests.get(url + "/quality_control/report/" + uid)
    assert r.status_code == 200

    # delete quality control
    payload = {'id': uid}
    r = requests.delete(url + "/quality_control/delete", data=payload, headers=headers)
    assert r.status_code == 200


    # check deleted
    r = requests.get(url + "/quality_control/list")
    assert r.status_code == 200
    todos = set()
    for res in r.json():
        todos.add(res['id'])
    assert uid in todos


