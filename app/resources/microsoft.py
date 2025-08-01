from flask import session
import requests
import identity.web

from queries.cql_queries import *
from resources.globals import Globals


auth = identity.web.Auth(
    session=session,
    authority=Globals.MS_ENTRA_ID_AUTHORITY,
    client_id=Globals.MS_ENTRA_ID_CLIENT_ID,
    client_credential=Globals.MS_ENTRA_ID_CLIENT_SECRET,
)


def generate_signin_link(url):
    return auth.log_in(scopes=Globals.MS_ENTRA_ID_SCOPE, redirect_uri=url)


def get_tokens(auth_response):
    result = auth.complete_log_in(auth_response)
    if "error" in result or len(result) == 0:
        raise Exception("An error occurred during the Microsoft sign-in process. Please clear your browser cache and try again.")
    return result


def get_user():
    return auth.get_user()


def _call_api(endpoint_key):
    token = auth.get_token_for_user(Globals.MS_ENTRA_ID_SCOPE)
    if "error" in token:
        raise Exception("Please sign in again via Microsoft.")
    return requests.get(
        Globals.MS_ENTRA_ID_ENDPOINTS[endpoint_key],
        headers={'Authorization': 'Bearer ' + token['access_token']},
        timeout=30,
    ).json()


def _org_response_unavailable(response_json):
    if 'error' in response_json and "Unable to find target address" in response_json['error']['message']:
        return True
    return False


def _determine_account_type(me, org):
    user_id = me['id'].replace("-", "")
    if len(user_id) == 32 and not _org_response_unavailable(org) and len(org['value'][0]['id'].replace("-", "")) == 32:
        if me['accountEnabled']:
            return 'ORG'  # School or work account
        else:
            raise Exception("Your account has been disabled by your organisation.")
    elif len(user_id) == 16 and _org_response_unavailable(org):
        return 'PER'  # Personal account
    else:
        raise Exception("Cannot determine Microsoft account type.")


def get_user_and_org_info():
    ms_me = _call_api('me')
    ms_org = _call_api('org')
    account_type = _determine_account_type(ms_me, ms_org)
    result = {
        'type': account_type,
        'user': {
            'id': ms_me['id'],
            'mail': ms_me['mail'],
            'surname': ms_me['surname'],
            'givenName': ms_me['givenName']
        }
    }
    if account_type == 'ORG':
        ms_org = ms_org['value'][0]
        result.update({
            'user_org': {
                'jobTitle': ms_me['jobTitle'],
                'department': ms_me['department']
            },
            'organization': {
                'id': ms_org['id'],
                'displayName': ms_org['displayName'],
                'verifiedDomains': [d['name'] for d in ms_org['verifiedDomains']]
            }
        })
    return result
