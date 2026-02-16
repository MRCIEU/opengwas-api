from flask import Blueprint
from .index import contributions_index_bp

contributions_bp = Blueprint('contributions', __name__)

contributions_bp.register_blueprint(contributions_index_bp, url_prefix='')
