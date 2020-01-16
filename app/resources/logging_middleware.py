from resources.auth import get_user_email
import logging

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
            path = environ['PATH_INFO']
        except Exception:
            path = None

        try:
            method = environ['REQUEST_METHOD']
        except Exception:
            method = None

        logger = logging.LoggerAdapter(logger_event, dict(path=path, method=method, user=user_email))
        logger.info(None)

        return self.app(environ, start_response)
