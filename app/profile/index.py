from flask import Blueprint, render_template, g
from flask_login import login_required, current_user

from queries.cql_queries import *
from resources.globals import Globals
from middleware.limiter import limiter, get_tiered_allowance, get_key_func_uid


profile_index_bp = Blueprint('index', __name__)


@profile_index_bp.route('')
@login_required
def index():
    org, membership = get_org_and_membership_from_user(current_user['uid']) if current_user['tier'] == 'ORG' else (None, None)
    org_tooltip = ""
    if org:
        if membership:
            org_tooltip = "The following information was provided by Microsoft when you use Single Sign-On (SSO)."
        else:
            org_tooltip = "The following information was inferred from the domain name of your email address."

    g.user = current_user
    return render_template('users/index.html',
                           user=current_user, globals_tiers=Globals.USER_TIERS, org=org, org_tooltip=org_tooltip, membership=membership,
                           tiered_allowance=get_tiered_allowance(), root_url=Globals.app_config['root_url'])


@profile_index_bp.route('/test_allowance')
@login_required
def get_allowance():
    g.user = current_user
    with limiter.shared_limit(limit_value=get_tiered_allowance, scope='tiered_allowance', key_func=get_key_func_uid, deduct_when=lambda flask_response: False):
        pass
    return {}
