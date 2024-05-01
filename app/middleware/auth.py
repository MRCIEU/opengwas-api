from flask import request, g
from functools import wraps
from werkzeug.exceptions import Unauthorized

from resources.jwt import validate_jwt


def jwt_required(f):
    @wraps(f)
    def _decorator(*args, **kwargs):
        if request.headers.get('Authorization') is None:
            raise Unauthorized("From 1st May 2024 you must provide a token (JWT) alongside most of your requests. Read more at https://api.opengwas.io/ and also check for the latest version at https://mrcieu.github.io/ieugwasr/")
        g.user = validate_jwt(request.headers.get('Authorization', '').replace("Bearer ", ""))
        return f(*args, **kwargs)
    return _decorator


def get_uid(error_on_none=False):
    if 'user' not in g:
        return Unauthorized("Unable to get uid. Please provide your token.") if error_on_none else None
    return g.user['uid']


def get_user_source(error_on_none=False):
    if 'user' not in g or 'source' not in g.user:
        return Unauthorized("Unable to get user source. Please provide your token.") if error_on_none else 'NONE'
    return g.user['source']
