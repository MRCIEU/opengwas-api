from flask import make_response, request, g
from flask_limiter import Limiter, RequestLimit, HEADERS
from flask_limiter.util import get_remote_address
import datetime

from resources.globals import Globals
from resources.redis import Redis
from .auth import get_user_tier, get_uid


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
    storage_uri='redis://:' + Globals.app_config['redis']['oci']['pass'] + '@' + Globals.app_config['redis']['oci']['host'] + ':' + Globals.app_config['redis']['oci']['port'] + '/1',
    storage_options={
        "connection_pool": Redis().conn['limiter'].connection_pool
    }
)


def get_allowance_by_user_tier():
    user_tier = get_user_tier()
    return Globals.ALLOWANCE_BY_USER_TIER[user_tier]


def get_key_func_uid():
    uid = get_uid()
    return uid if uid is not None else get_remote_address()


@limiter.request_filter
def header_whitelist():
    return any([
        request.headers.get('X-TEST-MODE-KEY', 'default_value') == Globals.app_config['test']['static_token'],
        request.headers.get('X-TEST-NO-RATE-LIMIT-KEY', 'default_value') == Globals.app_config['test']['no_rate_limit_key']
    ])
