from flask import request, Flask
from flask.sessions import SecureCookieSessionInterface, SessionMixin
from flask_session.sessions import RedisSessionInterface

from .redis import Redis


class NoCookieSessionInterface(SecureCookieSessionInterface):
    def should_set_cookie(self, app: Flask, session: SessionMixin) -> bool:
        return False


# Disable sessions
# https://stackoverflow.com/questions/50162502/disable-session-cookie-generation-in-python-flask-login
class CustomRedisSessionInterface(RedisSessionInterface):
    def __init__(self):
        super(CustomRedisSessionInterface, self).__init__(Redis().conn['session'], 'session:', False, False, 32)

    @staticmethod
    def _path_requires_session():
        if request.path.startswith('/probe') or request.path.startswith('/api'):
            return False
        return True

    def should_set_cookie(self, *args, **kwargs):
        return True if self._path_requires_session() else False

    def save_session(self, *args, **kwargs):
        return super(CustomRedisSessionInterface, self).save_session(*args, **kwargs) if self._path_requires_session() else False
