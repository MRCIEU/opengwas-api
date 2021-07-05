import flask
import logging
from os import path, walk
from resources.globals import Globals
from apis import api
from resources.neo4j import Neo4j
from apis.status import check_all, count_elastic_records, count_neo4j_datasets
from flask import request, has_request_context
from resources.logging_middleware import LoggerMiddleWare

def index():
    status = check_all()
    elastic_counts = count_elastic_records()
    neo4j_counts = count_neo4j_datasets()
    return flask.render_template('index.html', status=status, elastic_counts=elastic_counts, neo4j_counts=neo4j_counts)

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

setup_event_logger('event-log', Globals.LOG_FILE)
setup_logger('debug-log', Globals.LOG_FILE_DEBUG, level=logging.DEBUG, disabled=True)
setup_logger('query-log', Globals.LOG_FILE_QUERY, level=logging.DEBUG, disabled=False)


print("Starting MRB API v{}".format(Globals.VERSION))
app = flask.Flask(__name__, static_folder="static")

app.wsgi_app = LoggerMiddleWare(app.wsgi_app)
app.add_url_rule('/', 'index', index)

app.config.SWAGGER_UI_DOC_EXPANSION = 'list'
app.config['MAX_CONTENT_LENGTH'] = 7.5e+8
app.teardown_appcontext(Neo4j.close_db)
api.init_app(app)

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
