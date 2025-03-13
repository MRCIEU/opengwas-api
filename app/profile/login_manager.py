from flask import flash, redirect, url_for
from flask_login import LoginManager, login_user, current_user, logout_user
from functools import wraps

from queries.user_node import User

login_manager = LoginManager()
login_manager.login_view = '/'


@login_manager.user_loader
def load_user(uid):
    user = User.get_node(uid)
    return None if user.is_blocked() else user


def signin_user(user):
    uid = user['uid']
    user = load_user(uid)
    if user is None:
        flash('Please try again. UID: ' + uid, 'danger')
        return redirect(url_for('/'))
    login_user(user)
    return current_user


def signout_user():
    logout_user()


def role_required(role):
    def _decorator(f):
        @wraps(f)
        def _check_role(*args, **kwargs):
            if 'roles' not in current_user or role not in current_user['roles']:
                return login_manager.unauthorized()
            return f(*args, **kwargs)
        return _check_role
    return _decorator
