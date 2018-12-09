import PySQLPool
from elasticsearch import Elasticsearch
import json
import re

VERSION = '0.2.0'


# Toggle for local vs deployed
ES_CONF = "./conf_files/es_conf_local.json"
# ES_CONF = "./conf_files/es_conf.json"

PLINK = './ld_files/plink1.90'
LD_REF = './ld_files/data_maf0.01_rs'
TMP_FOLDER = './tmp/'
OAUTH2_URL = 'https://www.googleapis.com/oauth2/v1/tokeninfo?access_token='
USERINFO_URL = 'https://www.googleapis.com/oauth2/v1/userinfo?alt=json&access_token='
MYSQL_DB = "./conf_files/mysql.json"
LOG_FILE = "./logs/mrbaseapi.log"
LOG_FILE_DEBUG = "./logs/mrbaseapi-debug.log"

with open(MYSQL_DB) as f:
	mrbase_config = json.load(f)

dbConnection = PySQLPool.getNewConnection(**mrbase_config)

with open(ES_CONF) as f:
	es_conf = json.load(f)

with open(MYSQL_DB) as f:
	mrbase_config = json.load(f)

dbConnection = PySQLPool.getNewConnection(**mrbase_config)

#connect to elasticsearch
es = Elasticsearch(
		[{'host': es_conf['host'],'port': es_conf['port']}],
		#http_auth=(es_conf['user'], es_conf['password']),
)

mrb_batch='MRB'
study_batches=[mrb_batch,'UKB-a','UKB-b','UKB-c','pQTL-a','eqtl-a']

