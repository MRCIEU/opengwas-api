from flask import Blueprint, render_template, g
from flask_login import login_required, current_user

from queries.cql_queries import *
from resources.globals import Globals
from middleware.limiter import limiter, get_allowance_by_user_source, get_key_func_uid


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
    return render_template('profile/index.html',
                           user=current_user, globals_sources=Globals.USER_SOURCES, org=org, org_tooltip=org_tooltip, membership=membership,
                           allowance_by_user_source=get_allowance_by_user_source(), root_url=Globals.app_config['root_url'])


@profile_index_bp.route('/data')
@login_required
def gdpr():
    g.user = current_user
    computed_org, computed_membership = get_org_and_membership_from_user(current_user['uid']) if current_user['tier'] == 'ORG' else (None, None)
    return render_template('profile/data.html', user=current_user, globals_sources=Globals.USER_SOURCES, computed_org=computed_org, computed_membership=computed_membership)


@profile_index_bp.route('/test_allowance')
@login_required
def get_allowance():
    g.user = current_user
    with limiter.shared_limit(limit_value=get_allowance_by_user_source, scope='allowance_by_user_source', key_func=get_key_func_uid, deduct_when=lambda flask_response: False):
        pass
    return {}
