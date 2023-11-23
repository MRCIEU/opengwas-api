from flask_login import LoginManager, login_user, current_user, logout_user

from queries.user_node import User

login_manager = LoginManager()
login_manager.login_view = '/'


@login_manager.user_loader
def load_user(uid):
    return User.get_node(uid)


def signin_user(user):
    login_user(load_user(user['uid']))
    return current_user


def sign_out_user():
    logout_user()
