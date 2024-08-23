from flask import Blueprint, render_template
from flask_login import login_required

from profile.login_manager import role_required
from profile.token import get_token
from queries.cql_queries import *


admin_index_bp = Blueprint('index', __name__)


@admin_index_bp.route('')
@login_required
@role_required('admin')
def index():
    return render_template('admin/index.html')


@admin_index_bp.route('/token')
@login_required
@role_required('admin')
def get_token_plaintext():
    return get_token(preview=False)


@admin_index_bp.route('/datasets/review')
@login_required
@role_required('admin')
def dataset_review():
    return render_template('admin/datasets/review.html')
