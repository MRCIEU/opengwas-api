import requests
from token import get_mrbase_access_token

token = get_mrbase_access_token()


## GET

def test_assoc_get1():
	r = requests.get("http://localhost:8019/assoc/2/rs234")
	assert r.status_code == 200 and len(r.json()) == 1

def test_assoc_get2():
	r = requests.get("http://localhost:8019/assoc/2,987/rs234")
	assert r.status_code == 200 and len(r.json()) == 1

def test_assoc_get3():
	r = requests.get("http://localhost:8019/assoc/2,987,7/rs234")
	assert r.status_code == 200 and len(r.json()) == 2

def test_assoc_get4():
	r = requests.get("http://localhost:8019/assoc/2,987,7/rs234,rs123")
	assert r.status_code == 200 and len(r.json()) == 4

def test_assoc_get5():
	headers = {'X-API-TOKEN': token}
	r = requests.get("http://localhost:8019/assoc/2,987,7/rs234,rs123", headers=headers)
	assert r.status_code == 200 and len(r.json()) == 6


## POST

# Should return json entries for each study
def test_assoc_post1():
	headers = {'X-API-TOKEN': 'NULL'}
	payload = {'id': [2,7,987], 'rsid': ['rs234','rs123']}
	r = requests.post("http://localhost:8019/assoc", data=payload, headers=headers)
	assert r.status_code == 200 and len(r.json()) == 4

def test_assoc_post2():
	headers = {'X-API-TOKEN': token}
	payload = {'id': [2,7,987], 'rsid': ['rs234','rs123']}
	r = requests.post("http://localhost:8019/assoc", data=payload, headers=headers)
	assert r.status_code == 200 and len(r.json()) == 6

def test_assoc_post3():
	headers = {'X-API-TOKEN': token}
	payload = {'id': [1,2], 'rsid': ['rs6689306']}
	r = requests.post("http://localhost:8019/assoc", data=payload, headers=headers)
	assert r.status_code == 200 and len(r.json()) == 0

def test_assoc_post4():
	headers = {'X-API-TOKEN': token}
	payload = {'id': [1,2], 'rsid': ['rs6689306'], 'proxies': 1}
	r = requests.post("http://localhost:8019/assoc", data=payload, headers=headers)
	assert r.status_code == 200 and len(r.json()) == 2

def test_assoc_post5():
	headers = {'X-API-TOKEN': token}
	payload = {'id': [1,2], 'rsid': ['rs234','rs123','rs6689306']}
	r = requests.post("http://localhost:8019/assoc", data=payload, headers=headers)
	assert r.status_code == 200 and len(r.json()) == 4

def test_assoc_post6():
	headers = {'X-API-TOKEN': token}
	payload = {'id': [1,2], 'rsid': ['rs234','rs123','rs6689306'], 'proxies': 1}
	r = requests.post("http://localhost:8019/assoc", data=payload, headers=headers)
	assert r.status_code == 200 and len(r.json()) == 6


