from functools import wraps
from flask_login import LoginManager, login_user, current_user, logout_user

from queries.user_node import User

login_manager = LoginManager()
login_manager.login_view = '/'


@login_manager.user_loader
def load_user(uid):
    return User.get_node(uid)


def signin_user(user):
    user = load_user(user['uid'])
    login_user(user)
    return current_user


def signout_user():
    logout_user()


def role_required(role):
    def _decorator(f):
        @wraps(f)
        def _check_role(*args, **kwargs):
            if 'role' not in current_user or role not in current_user['role']:
                return login_manager.unauthorized()
            return f(*args, **kwargs)
        return _check_role
    return _decorator
