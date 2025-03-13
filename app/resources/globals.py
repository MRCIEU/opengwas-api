import json
import platform
import os
import requests
from elasticsearch import Elasticsearch

from neo4j import GraphDatabase


class Globals:
    VERSION = '4.0.0'
    root_path = os.path.dirname(os.path.dirname(__file__))
    APP_CONF = os.path.join(root_path, 'vault/app_conf.json')
    AUTHTEXT = 'See the Authentication section of API tutorial page for details on how to authenticate.'

    """ Set environment files to toggle between local and production & private vs public APIs """
    with open(APP_CONF) as f:
        app_config = json.load(f)

        if os.environ.get('ENV') == 'production':
            print("Production")
            app_config = app_config['production']
            app_config['env'] = 'production'
            QC_WDL_PATH = "/app/resources/workflow/qc.wdl"
            ELASTIC_WDL_PATH = "/app/resources/workflow/elastic.wdl"
        else:
            print("Local")
            app_config = app_config['local']
            app_config['env'] = 'local'
            QC_WDL_PATH = os.path.join(root_path, 'resources', 'workflow', 'qc.wdl')
            ELASTIC_WDL_PATH = os.path.join(root_path, 'resources', 'workflow', 'elastic.wdl')

        if os.environ.get('ACCESS') == 'private':
            app_config['access'] = 'private'
        else:
            app_config['access'] = 'public'

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
    # CROMWELL_URL = 'http://' + app_config['cromwell']['host'] + ":" + str(app_config['cromwell']['port'])
    # CROMWELL_AUTH = requests.auth.HTTPBasicAuth(app_config['cromwell']['basic_auth_username'], app_config['cromwell']['basic_auth_passwd'])

    CHROMLIST = list(range(1, 24)) + ['X', 'Y', 'MT']

    # reduced lifetime see here: https://github.com/neo4j/neo4j-python-driver/issues/196
    dbConnection = GraphDatabase.driver(
        'bolt://' + app_config['neo4j']['host'] + ":" + str(app_config['neo4j']['port']),
        auth=(app_config['neo4j']['user'], app_config['neo4j']['passwd']), max_connection_lifetime=5
    )

    # connect to elasticsearch
    es = Elasticsearch([f"http://elastic:{app_config['es']['password']}@{app_config['es']['host']}:{app_config['es']['port']}"], verify_certs=False)

    all_batches = list(set(['-'.join(id.split('-', 2)[:2]) for id in dbConnection.session().run("MATCH (n:GwasInfo) RETURN COLLECT(n.id)").single()[0]]))
    public_batches = list(set(['-'.join(id.split('-', 2)[:2]) for id in dbConnection.session().run("MATCH (g:Group {name: 'public'})-[r:ACCESS_TO]->(n:GwasInfo) RETURN COLLECT(n.id)").single()[0]]))

    gwas_pos_prefix_indices = {}

    variant_index = "snp-base-v0.2"

    EMAIL_VERIFICATION_LINK_VALIDITY = 3600  # seconds

    USER_SOURCES = {
        'MS': "Microsoft",
        'GH': "GitHub",
        'EM': "Email verification",
        'NONE': "Anonymous (legacy)"
    }

    USER_GROUPS = {
        'ORG': "Organisational",
        'PER': "Personal",
        'NONE': "Unknown (legacy)"
    }

    USER_TIERS = {
        'NONE': "No allowance",
        'TRIAL': "Trial",
        'STANDARD': 'Standard',
        'COMMERCIAL': 'Commercial',
        'UOB': 'UOB'
    }

    MS_ENTRA_ID_AUTHORITY = "https://login.microsoftonline.com/common"
    MS_ENTRA_ID_CLIENT_ID = app_config['providers']['microsoft']['entra_id']['client_id']
    MS_ENTRA_ID_CLIENT_SECRET = app_config['providers']['microsoft']['entra_id']['client_secret']
    MS_ENTRA_ID_SCOPE = ["User.Read"]
    MS_ENTRA_ID_ENDPOINTS = {
        'me': 'https://graph.microsoft.com/v1.0/me?$select=accountEnabled,id,userPrincipalName,surname,givenName,mail,userType,jobTitle,creationType,createdDateTime,createdBy,department,identities,usageLocation,proxyAddresses',
        'org': 'https://graph.microsoft.com/v1.0/organization?$select=id,displayName,verifiedDomains'
    }

    GH_APPS_AUTH_URL = "https://github.com/login/oauth/authorize"
    GH_APPS_AUTH_CLIENT_ID = app_config['providers']['github']['apps']['client_id']
    GH_APPS_AUTH_CLIENT_SECRET = app_config['providers']['github']['apps']['client_secret']
    GH_APPS_AUTH_ENDPOINTS = {
        'token': 'https://github.com/login/oauth/access_token',
        'user_emails': 'https://api.github.com/user/emails'
    }

    app_config['rsa_keys'] = {}
    with open(os.path.join(root_path, 'vault/api-jwt.key'), 'r') as f:
        app_config['rsa_keys']['private'] = f.read()
    with open(os.path.join(root_path, 'vault/api-jwt.pub'), 'r') as f:
        app_config['rsa_keys']['public'] = f.read()

    app_config['oci']['auth']['key_file'] = os.path.join(root_path, 'vault/oci.pem')

    JWT_VALIDITY = 14 * 86400  # seconds

    # https://flask-limiter.readthedocs.io/en/stable/configuration.html#ratelimit-string
    ALLOWANCE_BY_USER_TIER = {
        'UOB': '400000 per 10 minutes',
        'COMMERCIAL': '100000 per 10 minutes',
        'STANDARD': '100000 per 10 minutes',
        'TRIAL': '100 per 10 minutes',
        'NONE': '0 per 10 minutes'
    }

    SURVEY_FORMS = {
        'user_info': 'wbrKW1'
    }

    DATASET_ADDED_BY_STATE = {  # No state for released dataset
        0: 'Metadata created',
        1: 'QC in progress',  # crontab to update this field to 3 and send email
        2: 'QC completed',
        3: 'Pending approval',
        4: 'Release in progress'  # crontab to clear this field and send email
    }
