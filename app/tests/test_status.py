import requests

# Status check
def test_status():
	r = requests.get("http://localhost:8019/status")
	assert r.status_code == 200
