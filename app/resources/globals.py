from elasticsearch import Elasticsearch
import json
import platform
import os
from neo4j import GraphDatabase
import redis


class Globals:
    VERSION = '3.8.7'
    root_path = os.path.dirname(os.path.dirname(__file__))
    APP_CONF = os.path.join(root_path, 'app_conf.json')
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
    ES_HOST=app_config['es']['host']
    ES_PORT=app_config['es']['port']
    es = Elasticsearch([f"{ES_HOST}:{ES_PORT}"])

    all_batches = list(set(['-'.join(b['n.id'].split('-',2)[:2]) for b in dbConnection.session().run("match (n:GwasInfo) return n.id").data()]))

    public_batches = list(set(['-'.join(b['n.id'].split('-',2)[:2]) for b in dbConnection.session().run("match (g:Group {name: 'public'})-[r:ACCESS_TO]->(n:GwasInfo) return n.id").data()]))

    variant_index = "snp-base-v0.2"

    EMAIL_VERIFICATION_LINK_VALIDITY = 3600  # seconds

    JWT_VALIDITY = 14 * 86400  # seconds

    SESSION = {
        'SESSION_TYPE': 'redis',
        'SESSION_REDIS': redis.from_url('redis://:' + app_config['redis']['pass'] + '@' + app_config['redis']['host'] + ':' + app_config['redis']['port'])
    }

    USER_TIERS = {
        'ORG': "Organisational",
        'PER': "Personal"
    }

    MS_ENTRA_ID_AUTHORITY = "https://login.microsoftonline.com/common"
    MS_ENTRA_ID_CLIENT_ID = app_config['providers']['microsoft']['entra_id']['client_id']
    MS_ENTRA_ID_CLIENT_SECRET = app_config['providers']['microsoft']['entra_id']['client_secret']
    MS_ENTRA_ID_SCOPE = ["User.Read"]
    MS_ENTRA_ID_ENDPOINTS = {
        'me': 'https://graph.microsoft.com/v1.0/me?$select=accountEnabled,id,userPrincipalName,surname,givenName,mail,userType,jobTitle,creationType,createdDateTime,createdBy,department,identities,usageLocation,proxyAddresses',
        'org': 'https://graph.microsoft.com/v1.0/organization?$select=id,displayName,verifiedDomains'
    }
