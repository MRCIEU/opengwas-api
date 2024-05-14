from flask import Blueprint
from .index import admin_index_bp

admin_bp = Blueprint('admin', __name__)

admin_bp.register_blueprint(admin_index_bp, url_prefix='')
