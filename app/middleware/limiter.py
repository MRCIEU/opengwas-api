from flask import make_response
from flask_limiter import Limiter, RequestLimit
from flask_limiter.util import get_remote_address
import datetime

from resources.globals import Globals
from middleware.auth import get_tier, get_uid


def make_429_response(request_limit: RequestLimit):
    return make_response({
        "message": "Too many requests. Allowance: {}. Please try again after {}."
            .format(request_limit.limit, datetime.datetime.strftime(datetime.datetime.fromtimestamp(request_limit.reset_at).astimezone(), '%Y-%m-%d %H:%M %Z'))
    }, 429)


limiter = Limiter(
    key_func=get_remote_address,
    strategy='fixed-window-elastic-expiry',
    on_breach=make_429_response,
    storage_uri='redis://:' + Globals.app_config['redis']['pass'] + '@' + Globals.app_config['redis']['host'] + ':' + Globals.app_config['redis']['port'] + '/1',
)


def get_tiered_allowance():
    return Globals.RATE_ALLOWANCE[get_tier()]


def get_key_func_uid():
    uid = get_uid()
    return uid if uid else 'anonymous'
