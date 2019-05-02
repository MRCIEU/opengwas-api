import hashlib
from resources.auth import get_user_email
import logging

logger = logging.getLogger('debug-log')
logger_event = logging.getLogger('event-log')


class LoggerMiddleWare(object):

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        try:
            user_email = get_user_email(environ['HTTP_X_API_TOKEN'])
        except Exception:
            user_email = None

        try:
            # TODO
            # result = hashlib.md5(environ['HTTP_X_FORWARDED_FOR'].split(',')[-1].strip())
            # ip_hash = result.hexdigest()
            ip_hash = environ['HTTP_X_FORWARDED_FOR']
        except Exception:
            ip_hash = None

        try:
            path = environ['PATH_INFO']
        except Exception:
            path = None

        try:
            method = environ['REQUEST_METHOD']
        except Exception:
            method = None

        i = "path: {0}; method: {1}; ip_hash: {2}; user_email: {3}".format(
            path,
            method,
            ip_hash,
            user_email)

        logger_event.info(i)

        return self.app(environ, start_response)
