from elasticsearch import Elasticsearch
import json
import platform
import os
from neo4j import GraphDatabase


class Globals:
    VERSION = '2.0.0'

    root_path = os.path.dirname(os.path.dirname(__file__))

    # Toggle for local vs deployed
    APP_CONF = os.path.join(root_path, 'conf_files', 'app_conf.json')
    PLINK = os.path.join(root_path, 'bin', 'plink' + '_' + platform.system())
    LD_REF = os.path.join(root_path, 'ld_files', 'data_maf0.01_rs')
    TMP_FOLDER = os.path.join(root_path, 'tmp')
    UPLOAD_FOLDER = os.path.join(os.sep, 'data', 'igd')
    LOG_FILE = os.path.join(os.sep, 'data', 'mrb_logs', 'mrbaseapi.log')
    LOG_FILE_DEBUG = os.path.join(os.sep, 'data', 'mrb_logs', 'mrbaseapi-debug.log')

    OAUTH2_URL = 'https://www.googleapis.com/oauth2/v1/tokeninfo?access_token='
    USERINFO_URL = 'https://www.googleapis.com/oauth2/v1/userinfo?alt=json&access_token='

    CROMWELL_URL = "http://ieu-db-interface.epi.bris.ac.uk:8000"

    """ Set environment files to toggle between local and production & private vs public APIs """
    with open(APP_CONF) as f:
        app_config = json.load(f)

        try:
            if os.environ['ENV'] == 'production':
                app_config = app_config['production']
                QC_WDL_PATH = "/app/resources/workflow/qc.wdl"
                ELASTIC_WDL_PATH = "/app/resources/workflow/elastic.wdl"
            else:
                app_config = app_config['local']
                QC_WDL_PATH = os.path.join(root_path, 'resources', 'workflow', 'qc.wdl')
                ELASTIC_WDL_PATH = os.path.join(root_path, 'resources', 'workflow', 'elastic.wdl')
        except KeyError as e:
            app_config = app_config['local']

        try:
            if os.environ['ACCESS'] == 'public':
                app_config['access'] = 'public'
            else:
                app_config['access'] = 'private'
        except KeyError as e:
            app_config['access'] = 'private'

    print("Params: {}".format(app_config))

    # reduced lifetime see here: https://github.com/neo4j/neo4j-python-driver/issues/196
    dbConnection = GraphDatabase.driver(
        'bolt://' + app_config['neo4j']['host'] + ":" + str(app_config['neo4j']['port']),
        auth=(app_config['neo4j']['user'], app_config['neo4j']['passwd']), max_connection_lifetime=5
    )

    # connect to elasticsearch
    es = Elasticsearch(
        [{'host': app_config['es']['host'], 'port': app_config['es']['port']}]
    )

    study_batches = ['IEU-a', 'UKB-a', 'UKB-b', 'UKB-c', 'pQTL-a', 'eqtl-a']
    private_batches=['pQTL-a','pQTL-b','eqtl-a','UKB-c']
