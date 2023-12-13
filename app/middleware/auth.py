from flask import request, g
from functools import wraps
from werkzeug.exceptions import Unauthorized

from resources.jwt import validate_jwt


def jwt_required(f):
    @wraps(f)
    def _decorator(*args, **kwargs):
        g.user = validate_jwt(request.headers.get('Authorization', '').replace("Bearer ", ""))
        return f(*args, **kwargs)
    return _decorator


def get_uid(error_on_none=False):
    if 'user' not in g:
        return Unauthorized("Unable to get uid for rate limiting. Please provide your token.") if error_on_none else None
    return g.user['uid']


def get_tier(error_on_none=False):
    if 'user' not in g or 'tier' not in g.user:
        return Unauthorized("Unable to get tier for rate limiting. Please provide your token.") if error_on_none else 'NONE'
    return g.user['tier']
