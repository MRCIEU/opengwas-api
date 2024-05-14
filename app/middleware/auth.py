from flask import request, g
from functools import wraps

from queries.cql_queries import get_user_by_email
from resources.jwt import validate_jwt
from resources.globals import Globals
from .errors import raise_error


def jwt_required(f):
    @wraps(f)
    def _decorator(*args, **kwargs):
        if request.headers.get('Authorization') is not None:
            g.user = validate_jwt(request.headers.get('Authorization', '').replace("Bearer ", ""))
        elif request.headers.get('X-TEST-MODE-KEY', 'default_value') == Globals.app_config['test']['static_token']:
            g.user = get_user_by_email(Globals.app_config['test']['uid']).data()['u']
        else:
            return raise_error('MISSING_TOKEN')
        return f(*args, **kwargs)
    return _decorator


def check_role(role):
    def _decorator(f):
        @wraps(f)
        def _check_role(*args, **kwargs):
            if 'user' not in g or 'role' not in g.user or role not in g.user['role']:
                return raise_error('NO_PRIVILEGE')
            return f(*args, **kwargs)
        return _check_role
    return _decorator


def get_uid(error_on_none=False):
    if 'user' not in g:
        return raise_error('NO_UID') if error_on_none else None
    return g.user['uid']


def get_user_source(error_on_none=False):
    if 'user' not in g or 'source' not in g.user:
        return raise_error('NO_UID_OR_SOURCE') if error_on_none else 'NONE'
    return g.user['source']
