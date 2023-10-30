from flask import request
from functools import wraps
from apis.users import validate_jwt


def jwt_required():
    def decorator(f):
        @wraps(f)
        def _decorator(*args, **kwargs):
            validate_jwt(request.headers.get('X-Api-JWT'))
            return f(*args, **kwargs)
        return _decorator
    return decorator
