from flask import Blueprint
from .login_manager import login_manager
from .index import users_index_bp
from .auth import users_auth_bp

users_bp = Blueprint('users', __name__)

users_bp.register_blueprint(users_index_bp, url_prefix='')
users_bp.register_blueprint(users_auth_bp, url_prefix='auth')
