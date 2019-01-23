import requests

OAUTH2_URL = 'https://www.googleapis.com/oauth2/v1/tokeninfo?access_token='


# USERINFO_URL = 'https://www.googleapis.com/oauth2/v1/userinfo?alt=json&access_token='


def get_user_email(token):
    url = OAUTH2_URL + str(token)
    res = requests.get(url)

    if res.status_code != 200:
        raise requests.exceptions.HTTPError

    data = res.json()

    if "email" in data:
        return data['email']
    else:
        return "NULL"