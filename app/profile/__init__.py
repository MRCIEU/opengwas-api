from flask import Blueprint
from .login_manager import login_manager
from .index import profile_index_bp
from .auth import profile_auth_bp
from .token import profile_token_bp

profile_bp = Blueprint('profile', __name__)

profile_bp.register_blueprint(profile_index_bp, url_prefix='')
profile_bp.register_blueprint(profile_auth_bp, url_prefix='auth')
profile_bp.register_blueprint(profile_token_bp, url_prefix='token')
