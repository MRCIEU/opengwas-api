from flask import request
from functools import wraps
from queries.cql_queries import get_user_by_email
from resources.globals import Globals
import jwt
from werkzeug.exceptions import BadRequest


def jwt_required():
    def decorator(f):
        @wraps(f)
        def _decorator(*args, **kwargs):
            validate_jwt(request.headers.get('X-Api-JWT'))
            return f(*args, **kwargs)
        return _decorator
    return decorator


def validate_jwt(token):
    try:
        payload = jwt.decode(token, Globals.JWT_KEY, algorithms=['HS256'])
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

    if payload['timestamp'] != user['jwt_timestamp']:
        raise BadRequest("Please generate a new token.")

    # TODO: add counter
    return user
