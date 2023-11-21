from flask import Blueprint, render_template
from flask_login import login_required, current_user

from queries.cql_queries import *
from resources.globals import Globals


users_index_bp = Blueprint('index', __name__)


@users_index_bp.route('/')
@login_required
def index():
    org, membership = get_org_and_membership_from_user(current_user['uid']) if current_user['tier'] == 'ORG' else (None, None)
    org_tooltip = ""
    if org:
        if membership:
            org_tooltip = "The following information was retrieved from Microsoft when you use Single Sign-On (SSO)."
        else:
            org_tooltip = "The following information was inferred from the domain name of your email address."

    return render_template('users/index.html', user=current_user, globals_tiers=Globals.USER_TIERS, org=org, org_tooltip=org_tooltip, membership=membership)
