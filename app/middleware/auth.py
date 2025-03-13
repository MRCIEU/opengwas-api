from flask import request, g
from functools import wraps

from queries.cql_queries import get_user_by_email
from resources.jwt import validate_jwt
from resources.globals import Globals
from .errors import raise_error


def check_role_is_sufficient(user_roles: list, requested_role: str):
    if requested_role in user_roles:  # Exact match
        return True
    if 'admin' in user_roles:  # Admin can do anything
        return True
    return False


def jwt_required(f):
    @wraps(f)
    def _decorator(*args, **kwargs):
        if request.headers.get('Authorization') is not None:
            g.user = validate_jwt(request.headers.get('Authorization', '').replace("Bearer ", ""))
            if g.user.is_blocked():
                return raise_error('INVALID_ACCOUNT')
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
            if 'user' not in g or not check_role_is_sufficient(g.user.get('roles', []), role):
                return raise_error('NO_PRIVILEGE')
            return f(*args, **kwargs)
        return _check_role
    return _decorator


def key_required(f):
    @wraps(f)
    def _decorator(*args, **kwargs):
        if request.headers.get('X-SERVICE-KEY', 'default_value') in Globals.app_config['service_keys'].values():
            pass
        else:
            return raise_error('MISSING_KEY')
        return f(*args, **kwargs)
    return _decorator


def get_uid(error_on_none=False):
    if 'user' not in g:
        return raise_error('NO_UID') if error_on_none else None
    return g.user['uid']


def get_user_tier(error_on_none=False):
    if 'user' not in g:
        return raise_error('NO_UID') if error_on_none else 'NONE'
    if 'is_trial' in g.user:
        return 'TRIAL'
    try:
        if g.user['uid'].split('@')[1] == 'bristol.ac.uk':
            return 'UOB'
    except:
        pass
    return 'STANDARD'
