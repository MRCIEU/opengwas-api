from flask import request, g
from functools import wraps
from werkzeug.exceptions import Unauthorized

from resources.auth import get_user_email
# from resources.jwt import validate_jwt


def jwt_required(f):
    @wraps(f)
    def _decorator(*args, **kwargs):
        # g.user = validate_jwt(request.headers.get('Authorization', '').replace("Bearer ", ""))
        g.user = {
            'uid': get_user_email(request.headers.get('X-Api-Token'))
        }
        return f(*args, **kwargs)
    return _decorator


def get_uid(error_on_none=False):
    if 'user' not in g:
        return Unauthorized("Unable to get uid for rate limiting. Please provide your token.") if error_on_none else None
    return g.user['uid']


def get_user_source(error_on_none=False):
    if 'user' not in g or 'source' not in g.user:
        return Unauthorized("Unable to get user source for rate limiting. Please provide your token.") if error_on_none else 'NONE'
    return g.user['source']
