from flask import Blueprint
from .index import contribution_index_bp

contribution_bp = Blueprint('contribution', __name__)

contribution_bp.register_blueprint(contribution_index_bp, url_prefix='')
