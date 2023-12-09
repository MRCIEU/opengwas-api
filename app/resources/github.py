from flask import session
import time
import requests

from resources import Globals


def request_tokens(request_args):
    if 'code' not in request_args:
        raise Exception("Missing auth code from GitHub.")

    result = requests.post(
        Globals.GH_APPS_AUTH_ENDPOINTS['token'],
        headers={
            'Accept': 'application/json'
        },
        data={
            'client_id': Globals.GH_APPS_AUTH_CLIENT_ID,
            'client_secret': Globals.GH_APPS_AUTH_CLIENT_SECRET,
            'code': request_args['code']
        },
        timeout=30
    ).json()
    if "error" in result:
        raise Exception("An error occurred during the GibHub sign-in process.")

    now = int(time.time()) - 30
    result['expires_on'] = now + result['expires_in']
    del result['expires_in']
    result['refresh_token_expires_on'] = now + result['refresh_token_expires_in']
    del result['refresh_token_expires_in']

    session['_github_token'] = result

    return result


def _get_token():
    if '_github_token' in session and session['_github_token']['expires_on'] >= int(time.time()):
        return session['_github_token']['access_token']
    else:
        raise Exception("Cannot find a valid access token for GitHub.")


def _call_api(endpoint_key):
    return requests.get(
        Globals.GH_APPS_AUTH_ENDPOINTS[endpoint_key],
        headers={
            'Authorization': 'Bearer ' + _get_token(),
            'X-GitHub-Api-Version': '2022-11-28'
        },
        timeout=30
    ).json()


def get_user_emails() -> list:
    result = []
    for email in _call_api('user_emails'):
        if email['verified'] and 'github.com' not in email['email']:  # Only keep verified, non-privacy email
            result.append(email['email'])

    return result
