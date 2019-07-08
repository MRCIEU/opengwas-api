import flask
from resources.globals import Globals
from apis import api
from resources.logging_middleware import LoggerMiddleWare
from resources.neo4j import Neo4j
from apis.status import check_all, count_elastic_records, count_neo4j_datasets
from logging import handlers
import logging


def index():
    status = check_all()
    elastic_counts = count_elastic_records()
    neo4j_counts = count_neo4j_datasets()
    return flask.render_template('index.html', status=status, elastic_counts=elastic_counts, neo4j_counts=neo4j_counts)


def setup_logger(name, log_file, level=logging.INFO):
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

    # Create the log message rotation file handler to the logger
    # 10000000 = 10 MB
    handler = handlers.RotatingFileHandler(log_file, maxBytes=100000000, backupCount=100)
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger


def setup_event_logger(name, log_file):
    formatter = logging.Formatter(
        '%(asctime)s %(msecs)d %(user)s %(threadName)s %(levelname)s %(path)s %(method)s',
        datefmt='%d-%m-%Y:%H:%M:%S'
    )

    # Create the log message rotation file handler to the logger
    # 10000000 = 10 MB
    handler = handlers.RotatingFileHandler(log_file, maxBytes=100000000, backupCount=100)
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)

    return logger


print("Starting MRB API v{}".format(Globals.VERSION))
app = flask.Flask(__name__, static_folder="static")

setup_event_logger('event-log', Globals.LOG_FILE)
setup_logger('debug-log', Globals.LOG_FILE_DEBUG, level=logging.DEBUG)

app.wsgi_app = LoggerMiddleWare(app.wsgi_app)
app.add_url_rule('/', 'index', index)

app.config.SWAGGER_UI_DOC_EXPANSION = 'list'
app.config['MAX_CONTENT_LENGTH'] = 7.5e+8
app.teardown_appcontext(Neo4j.close_db)
api.init_app(app)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=Globals.app_config['flask']['port'])
