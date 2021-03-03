from elasticsearch import Elasticsearch
import json
import platform
import os
from neo4j import GraphDatabase


class Globals:
    VERSION = '3.6.11'
    root_path = os.path.dirname(os.path.dirname(__file__))
    APP_CONF = os.path.join(root_path, 'conf_files', 'app_conf.json')
    AUTHTEXT = 'Public datasets can be queried without any authentication, but some studies are only accessible by specific users. To authenticate we use Google OAuth2.0 access tokens. See the [homepage](https://gwas-api.mrcieu.ac.uk/#authentication) for details on how to authenticate.'

    """ Set environment files to toggle between local and production & private vs public APIs """
    with open(APP_CONF) as f:
        app_config = json.load(f)

        if os.environ.get('ENV') == 'production':
            print("Production")
            app_config = app_config['production']
            QC_WDL_PATH = "/app/resources/workflow/qc.wdl"
            ELASTIC_WDL_PATH = "/app/resources/workflow/elastic.wdl"
        else:
            print("Local")
            app_config = app_config['local']
            QC_WDL_PATH = os.path.join(root_path, 'resources', 'workflow', 'qc.wdl')
            ELASTIC_WDL_PATH = os.path.join(root_path, 'resources', 'workflow', 'elastic.wdl')

        if os.environ.get('ACCESS') == 'public':
            app_config['access'] = 'public'
        else:
            app_config['access'] = 'private'

    print("Params: {}".format(app_config))

    PLINK = os.path.join(root_path, 'bin', 'plink' + '_' + platform.system())
    LD_POPULATIONS = ['EUR', 'SAS', 'EAS', 'AFR', 'AMR', 'legacy']
    LD_REF = {}
    for pop in LD_POPULATIONS:
        LD_REF[pop] = os.path.join(root_path, 'ld_files', pop)
    LD_REF['legacy'] = os.path.join(root_path, 'ld_files', 'data_maf0.01_rs_ref')

    AFL2 = {
        'vcf': os.path.join(root_path, 'ld_files', 'annotations.vcf.gz'),
        'tbi': os.path.join(root_path, 'ld_files', 'annotations.vcf.gz.tbi'),
        'rsidx': os.path.join(root_path, 'ld_files', 'annotations.vcf.gz.rsidx'),
        'snplist': os.path.join(root_path, 'ld_files', 'annotations.vcf.selected_snplist.json')
    }

    TMP_FOLDER = app_config['directories']['tmp']
    UPLOAD_FOLDER = app_config['directories']['upload']
    LOG_FILE = os.path.join(app_config['directories']['logs'], 'mrbaseapi.log')
    LOG_FILE_DEBUG = os.path.join(app_config['directories']['logs'], 'mrbaseapi-debug.log')
    LOG_FILE_QUERY = os.path.join(app_config['directories']['logs'], 'opengwasapi-query.log')
    STATIC_GWASINFO = os.path.join(app_config['directories']['upload'], 'gwasinfo.json')

    OAUTH2_URL = 'https://www.googleapis.com/oauth2/v1/tokeninfo?access_token='
    USERINFO_URL = 'https://www.googleapis.com/oauth2/v1/userinfo?alt=json&access_token='
    CROMWELL_URL = 'http://' + app_config['cromwell']['host'] + ":" + str(app_config['cromwell']['port'])

    CHROMLIST = list(range(1, 24)) + ['X', 'Y', 'MT']

    # reduced lifetime see here: https://github.com/neo4j/neo4j-python-driver/issues/196
    dbConnection = GraphDatabase.driver(
        'bolt://' + app_config['neo4j']['host'] + ":" + str(app_config['neo4j']['port']),
        auth=(app_config['neo4j']['user'], app_config['neo4j']['passwd']), max_connection_lifetime=5
    )

    # connect to elasticsearch
    es = Elasticsearch(
        [{'host': app_config['es']['host'], 'port': app_config['es']['port']}]
    )

    all_batches = list(set(['-'.join(b['n.id'].split('-',2)[:2]) for b in dbConnection.session().run("match (n:GwasInfo) return n.id").data()]))

    public_batches = list(set(['-'.join(b['n.id'].split('-',2)[:2]) for b in dbConnection.session().run("match (g:Group {name: 'public'})-[r:ACCESS_TO]->(n:GwasInfo) return n.id").data()]))

    variant_index = "snp-base-v0.2"
