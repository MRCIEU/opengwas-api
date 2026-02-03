import time

import requests
import os


metadata_template = {
        'id': f"test-a-{int(time.time())}",
        'pmid': 1234,
        'year': 2010,
        'mr': 1,
        'note': 'test',
        'build': 'HG19/GRCh37',
        'trait': 'TEST - DO NOT USE (Hip circumference)',
        'category': 'Risk factor',
        'subcategory': 'Anthropometric',
        'ontology': 'EFO:000000',
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
        'consortium': 'GIANT',
    }


def test_edit_permission(url):
    r = requests.post(url + "/edit/add", data=metadata_template)
    assert r.status_code == 401


def test_edit_add_delete_metadata(url, headers):
    payload = metadata_template.copy()

    # add record
    r = requests.post(url + "/edit/add", data=payload, headers=headers)
    gwas_id = str(r.json()['id'])
    assert r.status_code == 200 and isinstance(int(gwas_id.replace('test-a-', '')), int)

    # check present
    r = requests.get(url + "/edit/check/" + gwas_id, headers=headers)
    assert r.status_code == 200 and len(r.json()) == 1

    # edit metadata
    payload['pmid'] = '12345'
    payload['id'] = gwas_id
    r = requests.post(url + "/edit/edit", data=payload, headers=headers)
    assert r.status_code == 200

    # cannot edit other's metadata
    payload['pmid'] = '12345'
    payload['id'] = 'ieu-a-2'
    r = requests.post(url + "/edit/edit", data=payload, headers=headers)
    assert r.status_code == 403

    # check metadata
    r = requests.get(url + "/edit/check/" + gwas_id, headers=headers)
    assert r.status_code == 200

    # delete metadata
    r = requests.delete(url + "/edit/delete/" + gwas_id, data={
        'delete_metadata': 1
    }, headers=headers)
    assert r.status_code == 200

    # cannot delete other's metadata
    r = requests.delete(url + "/edit/delete/" + 'ieu-a-2', data={
        'delete_metadata': 1
    }, headers=headers)
    assert r.status_code == 403

    # check deleted
    r = requests.get(url + "/edit/check/" + gwas_id, headers=headers)
    assert r.status_code == 200 and len(r.json()) == 0

    # check not deleted everything else
    r = requests.post(url + "/gwasinfo", data={'id': ["ieu-a-2"]}, headers=headers)
    assert r.status_code == 200 and len(r.json()) == 1


def test_edit_upload_gzip(url, headers):
    payload = metadata_template.copy()

    # make new metadata
    r = requests.post(url + "/edit/add", data=payload, headers=headers)
    assert r.status_code == 200
    gwas_id = str(r.json()['id'])
    assert isinstance(int(gwas_id.replace('test-a-', '')), int)

    file_path = os.path.join('apis', 'tests', 'data', 'jointGwasMc_LDL.head.txt.gz')

    # upload file for this study
    r = requests.post(url + "/edit/upload", data={
        'id': gwas_id,
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

    # Check DAG run and task instances have been created
    r = requests.get(url + '/edit/state/' + gwas_id, headers=headers)
    assert r.status_code == 200
    rj = r.json()
    assert rj['dags']['qc']['dag_run']['dag_run_id'] == gwas_id
    assert len(rj['dags']['qc']['task_instances']) > 10

    time.sleep(30)

    r = requests.delete(url + "/edit/delete/" + gwas_id, data={
        'fail_remaining_tasks': 1,
        'delete_metadata': 1
    }, headers=headers)
    print(r.json())
    assert r.status_code == 200
