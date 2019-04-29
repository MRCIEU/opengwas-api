import requests


# Status check
def test_status(url):
    r = requests.get(url + "/status")
    assert r.status_code == 200
