import flask
from flask import request, url_for
from flask_session.sessions import RedisSessionInterface, NullSessionInterface
from flask_login import current_user
from werkzeug.middleware.proxy_fix import ProxyFix
import logging
import os
import time
from os import path, walk
from datetime import datetime

from apis import api_bp
from resources import microsoft
from resources.globals import Globals
from resources.neo4j import Neo4j
from resources.logging_middleware import LoggerMiddleWare
from middleware.limiter import limiter
from users import users_bp, login_manager


# Disable sessions
# https://stackoverflow.com/questions/50162502/disable-session-cookie-generation-in-python-flask-login
class CustomRedisSessionInterface(RedisSessionInterface):
    def __init__(self):
        super(CustomRedisSessionInterface, self).__init__(Globals.SESSION_REDIS, 'session:')

    def _path_requires_session(self):
        if request.path in ['/healthcheck']:
            return False
        return True

    def should_set_cookie(self, *args, **kwargs):
        return True if self._path_requires_session() else False

    def save_session(self, *args, **kwargs):
        return super(CustomRedisSessionInterface, self).save_session(*args, **kwargs) if self._path_requires_session() else False


def setup_logger(name, log_file, level=logging.INFO, disabled=False):
    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s %(filename)s:%(lineno)d %(message)s'
        )

    handler = logging.FileHandler(log_file)
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    logger.disabled = disabled

    return logger


def setup_event_logger(name, log_file):
    formatter = logging.Formatter(
        '%(asctime)s %(msecs)d %(user)s %(remote_addr)s %(threadName)s %(levelname)s %(path)s %(method)s',
        datefmt='%d-%m-%Y:%H:%M:%S'
    )
    
    handler = logging.FileHandler(log_file)
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    return logger


def show_index():
    api_index_href = 'http://api.opengwas.io' if os.environ.get('ENV') == 'production' else url_for('api.root')
    return flask.render_template('index.html', api_index_href=api_index_href, current_user=current_user, **microsoft.generate_signin_link(url_for('users.auth.signup_via_microsoft', _external=True)))


def healthcheck():
    return {
        'time': int(time.time())
    }


# Let's Encrypt ACME challenge
def acme():
    return "mdwmQ9KELEMI3-T3kqCL4HLBiKOSRllC3PUkaTkQr6k.zDm77IFw4JnpIjshtRK4waD-ibCJOaVSKngPHpp3teQ"


setup_event_logger('event-log', Globals.LOG_FILE)
setup_logger('debug-log', Globals.LOG_FILE_DEBUG, level=logging.DEBUG, disabled=True)
setup_logger('query-log', Globals.LOG_FILE_QUERY, level=logging.DEBUG, disabled=True)


print("Starting MRB API v{}".format(Globals.VERSION))
app = flask.Flask(__name__, static_folder="static")

app.wsgi_app = LoggerMiddleWare(app.wsgi_app)

app.config.SWAGGER_UI_DOC_EXPANSION = 'list'
app.config['MAX_CONTENT_LENGTH'] = 7.5e+8
app.config.update(Globals.app_config['email'])

app.teardown_appcontext(Neo4j.close_db)

# https://flask-limiter.readthedocs.io/en/stable/recipes.html#deploying-an-application-behind-a-proxy
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)
# https://stackoverflow.com/a/76902054
limiter.init_app(app)

# Let's Encrypt ACME challenge
app.add_url_rule('/.well-known/acme-challenge/mdwmQ9KELEMI3-T3kqCL4HLBiKOSRllC3PUkaTkQr6k', '/acme', acme)
app.add_url_rule('/healthcheck', '/healthcheck', view_func=healthcheck)

if os.environ.get('ENV') == 'production':
    print('POOL', os.environ.get('POOL'))
    if os.environ.get('POOL') == 'api':
        app.session_interface = NullSessionInterface()
        app.register_blueprint(api_bp, url_prefix='')
    else:
        app.session_interface = CustomRedisSessionInterface()
        app.add_url_rule('/', '/', view_func=show_index)
        app.register_blueprint(users_bp, url_prefix='/users')
        login_manager.init_app(app)
else:
    app.session_interface = CustomRedisSessionInterface()
    app.add_url_rule('/', '/', view_func=show_index)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(users_bp, url_prefix='/users')
    login_manager.init_app(app)


if __name__ == "__main__":
    extra_dirs = ['templates','static']
    extra_files = extra_dirs[:]
    for extra_dir in extra_dirs:
        for dirname, dirs, files in walk(extra_dir):
            for filename in files:
                filename = path.join(dirname, filename)
                if path.isfile(filename):
                    extra_files.append(filename)
    app.run(host='0.0.0.0', port=Globals.app_config['flask']['port'], extra_files=extra_files)


@app.before_request
def check_test_mode():
    key = request.headers.get('X-Declare-Test-Mode-Key')
    if key and key == Globals.app_config['test']['key_declare_test_mode']:
        os.environ['TEST_MODE'] = 'True'
        # Disable flask-limiter
        limiter.enabled = False


@app.context_processor
def inject_metadata():
    return {
        'now': datetime.utcnow(),
        'version': Globals.VERSION
    }
