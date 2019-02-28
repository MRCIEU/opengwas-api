from elasticsearch import Elasticsearch
import json
import os.path
from neo4j import GraphDatabase
from resources._logger import logger2

VERSION = '0.2.0'

root_path = os.path.dirname(os.path.dirname(__file__))
logger2.debug("root path {}".format(root_path))

# Toggle for local vs deployed
APP_CONF = os.path.join(root_path, 'conf_files', 'app_conf.json')
PLINK = os.path.join(root_path, 'ld_files', 'plink1.90')
LD_REF = os.path.join(root_path, 'ld_files', 'data_maf0.01_rs')
TMP_FOLDER = os.path.join(root_path, 'tmp')
UPLOAD_FOLDER = os.path.join('data', 'bgc')
LOG_FILE = os.path.join(root_path, 'logs', 'mrbaseapi.log')
LOG_FILE_DEBUG = os.path.join(root_path, 'logs', 'mrbaseapi-debug.log')

logger2.debug("APP_CONF {}".format(APP_CONF))
logger2.debug("PLINK {}".format(PLINK))
logger2.debug("LD_REF {}".format(LD_REF))
logger2.debug("TMP_FOLDER {}".format(TMP_FOLDER))
logger2.debug("UPLOAD_FOLDER {}".format(UPLOAD_FOLDER))
logger2.debug("LOG_FILE {}".format(LOG_FILE))
logger2.debug("LOG_FILE_DEBUG {}".format(LOG_FILE_DEBUG))

OAUTH2_URL = 'https://www.googleapis.com/oauth2/v1/tokeninfo?access_token='
USERINFO_URL = 'https://www.googleapis.com/oauth2/v1/userinfo?alt=json&access_token='
ALLOWED_EXTENSIONS = {'txt'}

with open(APP_CONF) as f:
    app_config = json.load(f)
if os.path.isfile('local') is True:
    logger2.debug("local")
    app_config = app_config['local']
else:
    logger2.debug("production")
    app_config = app_config['production']

dbConnection = GraphDatabase.driver(
    'bolt://' + app_config['neo4j']['host'] + ":" + str(app_config['neo4j']['port']),
    auth=(app_config['neo4j']['user'], app_config['neo4j']['passwd'])
)

# connect to elasticsearch
es = Elasticsearch(
    [{'host': app_config['es']['host'], 'port': app_config['es']['port']}]
)

mrb_batch = 'MRB'
study_batches = [mrb_batch, 'UKB-a', 'UKB-b', 'UKB-c', 'pQTL-a', 'eqtl-a']
