from flask import Blueprint, render_template
from flask_login import login_required

from profile.login_manager import role_required
from profile.token import get_token
from queries.cql_queries import *


contributions_index_bp = Blueprint('index', __name__)


@contributions_index_bp.route('')
@login_required
@role_required('contributor')
def index():
    return render_template('contributions/index.html', container_width=1000)


@contributions_index_bp.route('/token')
@login_required
@role_required('contributor')
def get_token_plaintext():
    return get_token(preview=False)
