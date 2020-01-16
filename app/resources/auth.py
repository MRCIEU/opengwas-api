import requests

OAUTH2_URL = 'https://www.googleapis.com/oauth2/v1/tokeninfo?access_token='


# USERINFO_URL = 'https://www.googleapis.com/oauth2/v1/userinfo?alt=json&access_token='


def get_user_email(token):
    try:
        if token.lower() == 'null':
            return None
    except AttributeError:
        return None
    print(token)
    url = OAUTH2_URL + str(token)
    res = requests.get(url)
    print(url)
    if res.status_code == 400:
        raise requests.exceptions.HTTPError("Token has expired or is invalid.")

    if res.status_code != 200:
        raise requests.exceptions.HTTPError("Status code was {}".format(res.status_code))

    data = res.json()

    if "email" in data:
        return data['email']
    else:
        return None
