from flask import make_response
from flask_limiter import Limiter, RequestLimit
from flask_limiter.util import get_remote_address
import datetime

from resources.globals import Globals


def make_429_response(request_limit: RequestLimit):
    return make_response({
        "message": "Too many requests. Please try again later after {}."
            .format(datetime.datetime.strftime(datetime.datetime.fromtimestamp(request_limit.reset_at).astimezone(), '%Y-%m-%d %H:%M %Z'))
    }, 429)


limiter = Limiter(
    key_func=get_remote_address,
    strategy='fixed-window-elastic-expiry',
    on_breach=make_429_response,
    storage_uri='redis://:' + Globals.app_config['redis']['pass'] + '@' + Globals.app_config['redis']['host'] + ':' + Globals.app_config['redis']['port'] + '/1',
)
