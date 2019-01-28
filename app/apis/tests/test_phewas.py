import requests
from apis.tests.token import get_mrbase_access_token

token = get_mrbase_access_token()


## GET

def test_phewas_get1(url):
	r = requests.get(url + "/phewas/rs234")
	assert r.status_code == 200 and len(r.json()['data']) > 100


## POST

def test_phewas_post1(url):
	headers = {'X-API-TOKEN': token}
	payload = {'rsid': 'rs234'}
	r = requests.post(url + "/phewas", data=payload, headers=headers)
	assert r.status_code == 200 and len(r.json()['data']) 
