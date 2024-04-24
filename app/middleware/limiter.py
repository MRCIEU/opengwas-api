from flask import make_response, request, g
from flask_limiter import Limiter, RequestLimit, HEADERS
from flask_limiter.util import get_remote_address
import datetime

from resources.globals import Globals
from middleware.auth import get_user_source, get_uid


def make_429_response(request_limit: RequestLimit):
    return make_response({
        "message": "Too many requests. Allowance: {}. Please try again after {}."
            .format(request_limit.limit, datetime.datetime.strftime(datetime.datetime.fromtimestamp(request_limit.reset_at).astimezone(), '%Y-%m-%d %H:%M %Z'))
    }, 429)


limiter = Limiter(
    key_func=get_remote_address,
    strategy='fixed-window',
    headers_enabled=True,
    header_name_mapping={
        HEADERS.LIMIT: "X-Allowance-Limit",
        HEADERS.REMAINING: "X-Allowance-Remaining",
        HEADERS.RESET: "X-Allowance-Reset"
    },
    on_breach=make_429_response,
    storage_uri='redis://:' + Globals.app_config['redis']['pass'] + '@' + Globals.app_config['redis']['host'] + ':' + Globals.app_config['redis']['port'] + '/1'
)


def get_allowance_by_user_source():
    user_source = get_user_source()
    if 'user' in g and g.user['uid'].split('@')[1] == 'bristol.ac.uk':
        user_source = 'UOB'
    return Globals.ALLOWANCE_BY_USER_SOURCE[user_source]


def get_key_func_uid():
    uid = get_uid()
    return uid if uid is not None else get_remote_address()


@limiter.request_filter
def header_whitelist():
    return request.headers.get('X-TEST-MODE-KEY', None) == Globals.app_config['test']['test_mode_key']
