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
        raise Unauthorized("Invalid token. Visit https://api.opengwas.io to obtain one and make sure there are no extra or missing characters around the token when you copy and paste. (1) If you are using R/ieugwasr, R/TwoSampleMR or derived packages, please see https://mrcieu.github.io/ieugwasr/articles/guide.html#authentication (2) If you are building your own wrapper around our API, please add your token to the request header. Header name: 'Authorization'. Header value: 'Bearer your_token' (with whitespace and no quotes). See also: https://datatracker.ietf.org/doc/html/rfc6750#section-2.1")

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
