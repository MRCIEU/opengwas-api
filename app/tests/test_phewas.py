import requests
from token import get_mrbase_access_token

token = get_mrbase_access_token()


## GET

def test_phewas_get1():
	r = requests.get("http://localhost:8019/phewas/rs234")
	assert r.status_code == 200 and len(r.json()['data']) > 100


## POST

def test_phewas_post1():
	headers = {'X-API-TOKEN': token}
	payload = {'rsid': 'rs234'}
	r = requests.post("http://localhost:8019/phewas", data=payload, headers=headers)
	assert r.status_code == 200 and len(r.json()['data']) 
