import jwt
import time
from werkzeug.exceptions import Unauthorized

from queries.cql_queries import get_user_by_email
from resources.globals import Globals


def generate_jwt(uid, timestamp):
    result = jwt.encode({
        'iss': 'api.opengwas.io',
        'aud': 'api.opengwas.io',
        'sub': uid,
        'iat': timestamp,
        'exp': timestamp + Globals.JWT_VALIDITY
    }, Globals.app_config['rsa_keys']['private'], algorithm='RS256', headers={
        'kid': 'api-jwt'
    })
    return result


def generate_jwt_preview(uid, timestamp):
    result = generate_jwt(uid, timestamp).split(".")
    return "{}**************.********************.**************{}".format(result[0][:5], result[2][-6:])


def validate_jwt(token):
    try:
        payload = jwt.decode(token, Globals.app_config['rsa_keys']['public'], algorithms=['RS256'])
    except jwt.exceptions.InvalidSignatureError:
        raise Unauthorized("Invalid JWT signature.")
    except jwt.exceptions.DecodeError:
        raise Unauthorized("Invalid JWT header or payload.")

    user = get_user_by_email(payload['sub'])
    if user is None:
        raise Unauthorized('User does not exist or has been deactivated.')
    user = user.data()['u']
    if 'jwt_timestamp' not in user:
        raise Unauthorized('Invalid JWT.')

    if int(time.time()) > payload['iat'] + Globals.JWT_VALIDITY or payload['iat'] != user['jwt_timestamp']:
        # TODO: reset jwt_timestamp?
        raise Unauthorized("Please generate a new token.")

    # TODO: add counter
    return user
