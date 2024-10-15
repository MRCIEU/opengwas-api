from flask import Blueprint, render_template, g
from flask_login import login_required, current_user

from queries.cql_queries import *
from resources.globals import Globals
from middleware.auth import get_user_tier
from middleware.limiter import limiter, get_allowance_by_user_tier, get_key_func_uid


profile_index_bp = Blueprint('index', __name__)


@profile_index_bp.route('')
@login_required
def index():
    g.user = current_user
    return render_template('profile/index.html', user=current_user, globals_sources=Globals.USER_SOURCES,
                           globals_tiers=Globals.USER_TIERS, user_tier=get_user_tier(),
                           allowance_by_user_tier=get_allowance_by_user_tier(), root_url=Globals.app_config['root_url'])


@profile_index_bp.route('/data')
@login_required
def gdpr():
    g.user = current_user
    computed_org, computed_membership = get_org_and_membership_from_user(current_user['uid']) if current_user['group'] == 'ORG' else (None, None)
    return render_template('profile/data.html', user=current_user, globals_sources=Globals.USER_SOURCES, computed_org=computed_org, computed_membership=computed_membership)


@profile_index_bp.route('/test_allowance')
@login_required
def get_allowance():
    g.user = current_user
    with limiter.shared_limit(limit_value=get_allowance_by_user_tier, scope='allowance_by_user_tier', key_func=get_key_func_uid, deduct_when=lambda flask_response: False):
        pass
    return {}
