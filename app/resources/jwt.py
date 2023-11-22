import jwt
import time
from werkzeug.exceptions import BadRequest

from queries.cql_queries import get_user_by_email
from resources.globals import Globals


def generate_jwt(uid, timestamp):
    result = jwt.encode({
        'uid': uid,
        'timestamp': timestamp
    }, Globals.app_config['jwt']['key'], algorithm='HS256')
    return result


def generate_jwt_preview(uid, timestamp):
    result = generate_jwt(uid, timestamp).split(".")
    return "{}**************.********************.**************{}".format(result[0][:5], result[2][-6:])


def validate_jwt(token):
    try:
        payload = jwt.decode(token, Globals.app_config['jwt']['key'], algorithms=['HS256'])
    except jwt.exceptions.InvalidSignatureError:
        raise BadRequest("Invalid JWT signature.")
    except jwt.exceptions.DecodeError:
        raise BadRequest("Invalid JWT header or payload.")

    user = get_user_by_email(payload['uid'])
    if user is None:
        raise BadRequest('User does not exist or has been deactivated.')
    user = user.data()['u']
    if 'jwt_timestamp' not in user:
        raise BadRequest('Invalid JWT.')

    if int(time.time()) > payload['timestamp'] + Globals.JWT_VALIDITY or payload['timestamp'] != user['jwt_timestamp']:
        raise BadRequest("Please generate a new token.")

    # TODO: add counter
    return user
