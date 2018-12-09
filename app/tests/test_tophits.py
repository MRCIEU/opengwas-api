import requests
from token import get_mrbase_access_token

token = get_mrbase_access_token()

def test_tophits_post1():
	headers = {'X-API-TOKEN': 'NULL'}
	payload = {'id': [2,987], 'clump': 0}
	r = requests.post("http://localhost:8019/tophits", data=payload, headers=headers)
	assert r.status_code == 200 and len(r.json()) < 3000 and len(set([x.get('id') for x in r.json()])) == 1

def test_tophits_post2():
	headers = {'X-API-TOKEN': token}
	payload = {'id': [2,987], 'clump': 0}
	r = requests.post("http://localhost:8019/tophits", data=payload, headers=headers)
	assert r.status_code == 200 and len(r.json()) > 3000 and len(set([x.get('id') for x in r.json()])) == 2

def test_tophits_post3():
	headers = {'X-API-TOKEN': 'NULL'}
	payload = {'id': [2,987], 'clump': 1}
	r = requests.post("http://localhost:8019/tophits", data=payload, headers=headers)
	assert r.status_code == 200 and len(r.json()) < 80 and len(set([x.get('id') for x in r.json()])) == 1

def test_tophits_post4():
	headers = {'X-API-TOKEN': token}
	payload = {'id': [2,987], 'clump': 1}
	r = requests.post("http://localhost:8019/tophits", data=payload, headers=headers)
	assert r.status_code == 200 and len(r.json()) > 80 and len(set([x.get('id') for x in r.json()])) == 2
