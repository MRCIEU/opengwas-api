from flask import Blueprint
from flask_login import login_required, current_user
import datetime
import time

from queries.cql_queries import set_user_jwt_timestamp
from resources.jwt import generate_jwt, generate_jwt_preview
from resources.globals import Globals


profile_token_bp = Blueprint('token', __name__)


@profile_token_bp.route('')
@login_required
def get_token():
    if 'jwt_timestamp' not in current_user or not (jwt_timestamp := current_user['jwt_timestamp']) or int(time.time()) > jwt_timestamp + Globals.JWT_VALIDITY:
        return {}, 410

    return {
        'expiry': datetime.datetime.strftime(datetime.datetime.fromtimestamp(jwt_timestamp + Globals.JWT_VALIDITY).astimezone(), '%Y-%m-%d %H:%M:%S %Z'),
        'token': generate_jwt_preview(current_user['uid'], jwt_timestamp)
    }


@profile_token_bp.route('/generate')
@login_required
def generate_token():
    timestamp = int(time.time())
    token = generate_jwt(current_user['uid'], timestamp)
    set_user_jwt_timestamp(current_user['uid'], timestamp)

    expiry = timestamp + Globals.JWT_VALIDITY
    expiry_str = datetime.datetime.strftime(datetime.datetime.fromtimestamp(expiry).astimezone(), '%Y-%m-%d %H:%M:%S %Z')

    return {
        'expiry': expiry_str,
        'token': token
    }


