from flask import Blueprint, render_template
from flask_login import login_required

import datetime

from middleware.auth import get_user_tier
from middleware.limiter import get_allowance_by_user_tier
from profile.login_manager import role_required
from profile.token import get_token
from queries.cql_queries import *
from resources.globals import Globals


admin_users_bp = Blueprint('users', __name__)


@admin_users_bp.route('')
@login_required
@role_required('admin')
def users():
    return render_template('admin/users/index.html', container_width=1200)


@admin_users_bp.route('<uuid>')
@login_required
@role_required('admin')
def user(uuid):
    user = get_user_by_uuid(uuid)
    if user is not None:
        user = user.data()['u']

        def _convert_timestamp(unix_timestamp):
            return datetime.datetime.strftime(datetime.datetime.fromtimestamp(unix_timestamp).astimezone(), '%Y-%m-%d %H:%M:%S %Z')

        user['created'] = _convert_timestamp(user['created']) if 'created' in user else '(Missing data)'
        user['last_signin'] = _convert_timestamp(user['last_signin']) if 'last_signin' in user else '(Never)'
        user['jwt_timestamp'] = _convert_timestamp(user['jwt_timestamp']) if 'jwt_timestamp' in user else '(Never)'

        computed_org, computed_membership = get_org_and_membership_from_user(user['uid']) if user['group'] == 'ORG' else (None, None)

        return render_template('admin/users/user.html', user=user, globals_sources=Globals.USER_SOURCES,
                           globals_tiers=Globals.USER_TIERS, user_tier=get_user_tier(user=user),
                           allowance_by_user_tier=get_allowance_by_user_tier(user=user),
                           computed_org=computed_org, computed_membership=computed_membership)
    else:
        pass
