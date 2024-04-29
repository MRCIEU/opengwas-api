from flask import request
from flask_session.sessions import RedisSessionInterface, NullSessionInterface

from resources.globals import Globals


# Disable sessions
# https://stackoverflow.com/questions/50162502/disable-session-cookie-generation-in-python-flask-login
class CustomRedisSessionInterface(RedisSessionInterface):
    def __init__(self):
        super(CustomRedisSessionInterface, self).__init__(Globals.SESSION_REDIS, 'session:',False, False, 32)

    @staticmethod
    def _path_requires_session():
        if request.path.startswith('/probe') or request.path.startswith('/api'):
            return False
        return True

    def should_set_cookie(self, *args, **kwargs):
        return True if self._path_requires_session() else False

    def save_session(self, *args, **kwargs):
        return super(CustomRedisSessionInterface, self).save_session(*args, **kwargs) if self._path_requires_session() else False
