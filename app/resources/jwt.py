import jwt
import time
from werkzeug.exceptions import Unauthorized

from queries.user_node import User
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
        payload = jwt.decode(token, Globals.app_config['rsa_keys']['public'], algorithms=['RS256'], audience='api.opengwas.io')
    except Exception as e:
        raise Unauthorized("Invalid token. Please add your token to the request header. Header name: 'Authorization'. Header value: 'Bearer <your_token>'. To obtain a token, visit https://api.opengwas.io")

    try:
        user = User.get_node(payload['sub'])
    except LookupError:
        raise Unauthorized("User does not exist.")
    except Exception:
        raise Unauthorized("Unknown error.")

    if 'jwt_timestamp' not in user:
        raise Unauthorized("Please generate a new token.")

    if int(time.time()) > payload['iat'] + Globals.JWT_VALIDITY or payload['iat'] != user['jwt_timestamp']:
        # TODO: reset jwt_timestamp?
        raise Unauthorized("Please generate a new token.")

    return user
