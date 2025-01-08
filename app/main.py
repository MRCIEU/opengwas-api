from datetime import datetime
import gzip
import io
import logging
import os
import pickle
import shutil
import time

import flask
from flask_login import current_user
from werkzeug.middleware.proxy_fix import ProxyFix

from resources.globals import Globals
# from resources.logging_middleware import LoggerMiddleWare
from resources.neo4j import Neo4j
from queries.cql_queries import get_all_gwas_ids_by_n_id, get_public_batches_prefix
from resources._oci import OCIObjectStorage
from resources.sessions import NoCookieSessionInterface, CustomRedisSessionInterface
from middleware.before_request import before_api_request
from middleware.limiter import limiter
from apis import api_bp
from apis.status import check_ld_ref, check_1000g_vcf
from profile import profile_bp, login_manager
from contribution import contribution_bp
from admin import admin_bp


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
    return flask.render_template('index.html', root_url=Globals.app_config['root_url'], current_user=current_user)


def probe_health():
    disk_free_space = 0
    try:
        disk_free_space = shutil.disk_usage('/').free / 1048576
    except Exception:
        pass
    if disk_free_space >= 512:
        return {
            'time': int(time.time()),
            'disk_free_space_megabytes': disk_free_space
        }
    return {'message': "Disk free space too low"}, 503


def probe_readiness():
    if check_ld_ref() == "Available" and check_1000g_vcf() == "Available":
        return {'message': "LD files available"}, 200
    return {'message': "LD files unavailable"}, 503


def download_gwas_pos_prefix_indices():
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(OCIObjectStorage().object_storage_download('data-chunks', '0_pos_prefix_indices').data.content), mode='rb') as f:
            Globals.gwas_pos_prefix_indices = pickle.loads(f.read())
        logging.info('Successfully retrieved pos_prefix_indices')
    except Exception as e:
        logging.error('Unable to retrieve pos_prefix_indices')


def query_all_ids_and_batches():
    t0 = time.time()
    Globals.all_ids = get_all_gwas_ids_by_n_id()
    Globals.all_batches = list(set(['-'.join(gwas_id.split('-', 2)[:2]) for gwas_id in Globals.all_ids.values()]))
    # Globals.public_batches = get_public_batches_prefix()
    print(f"Loaded all_ids_and_batches in {time.time() - t0} seconds")


setup_event_logger('event-log', Globals.LOG_FILE)
setup_logger('debug-log', Globals.LOG_FILE_DEBUG, level=logging.DEBUG, disabled=True)
setup_logger('query-log', Globals.LOG_FILE_QUERY, level=logging.DEBUG, disabled=True)

logging.getLogger("neo4j.notifications").setLevel(logging.ERROR)

print("Starting MRB API v{}".format(Globals.VERSION))
app = flask.Flask(__name__, static_folder="static")

# app.wsgi_app = LoggerMiddleWare(app.wsgi_app)

app.config.SWAGGER_UI_DOC_EXPANSION = 'list'
app.config['MAX_CONTENT_LENGTH'] = 1.5e+9
app.config['SESSION_COOKIE_SECURE'] = True
app.config.update(Globals.app_config['email'])

app.config.update(Globals.app_config['mysql']['config'])
Globals.mysql.init_app(app)

app.teardown_appcontext(Neo4j.close_db)

# https://flask-limiter.readthedocs.io/en/stable/recipes.html#deploying-an-application-behind-a-proxy
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)
# https://stackoverflow.com/a/76902054
limiter.init_app(app)

app.add_url_rule('/probe/health', '/probe/health', view_func=probe_health)

if os.environ.get('GROUP') in ['prod', 'test']:
    print('COMPONENT', os.environ.get('COMPONENT'))
    if os.environ.get('COMPONENT') in ['api', 'api-light', 'api-ref', 'api-priv']:
        app.session_interface = NoCookieSessionInterface()
        app.add_url_rule('/probe/readiness', '/probe/readiness', view_func=probe_readiness)
        app.register_blueprint(api_bp, url_prefix='/api')
        with app.app_context():
            download_gwas_pos_prefix_indices()
            query_all_ids_and_batches()
            logging.getLogger('oci._vendor.urllib3.connectionpool').setLevel(logging.ERROR)

        @app.before_request
        def before_request():
            return before_api_request()

    elif os.environ.get('COMPONENT') == 'ui':
        app.session_interface = CustomRedisSessionInterface()
        app.add_url_rule('/', '/', view_func=show_index)
        app.register_blueprint(profile_bp, url_prefix='/profile')
        app.register_blueprint(contribution_bp, url_prefix='/contribution')
        app.register_blueprint(admin_bp, url_prefix='/admin')
        login_manager.init_app(app)
else:
    app.session_interface = CustomRedisSessionInterface()
    app.add_url_rule('/probe/readiness', '/probe/readiness', view_func=probe_readiness)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.add_url_rule('/', '/', view_func=show_index)
    app.register_blueprint(profile_bp, url_prefix='/profile')
    app.register_blueprint(contribution_bp, url_prefix='/contribution')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    login_manager.init_app(app)
    with app.app_context():
        download_gwas_pos_prefix_indices()
        query_all_ids_and_batches()

    @app.before_request
    def before_request():
        return before_api_request()


if __name__ == "__main__":
    extra_dirs = ['templates','static']
    extra_files = extra_dirs[:]
    for extra_dir in extra_dirs:
        for dirname, dirs, files in os.walk(extra_dir):
            for filename in files:
                filename = os.path.join(dirname, filename)
                if os.path.isfile(filename):
                    extra_files.append(filename)
    app.run(host='0.0.0.0', port=Globals.app_config['flask']['port'], extra_files=extra_files)


@app.context_processor
def inject_metadata():
    return {
        'now': datetime.utcnow(),
        'version': Globals.VERSION
    }
