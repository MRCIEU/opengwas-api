from flask import request
from flask_restx import Namespace, Resource
import requests
from requests.auth import HTTPBasicAuth
import os
import json

from resources.globals import Globals
from resources.neo4j import Neo4j
from resources._oci import OCIObjectStorage
from middleware.limiter import limiter

api = Namespace('status', description="Status of API and linked resources")


@api.route('')
@api.doc(description="Check services are running")
class Status(Resource):
    @api.doc(id='status_get', security=[])
    @limiter.limit('300 per hour')  # Max number of requests per IP
    def get(self):
        n_logs_past_hour = count_logs_past_hour()
        n_datasets = count_neo4j_datasets()

        match request.headers.get('X-API-STATUS-SERVICE-NAME', '').upper():
            case 'NEO4J':
                return Neo4j.check_running()
            case 'ES':
                return check_elastic()
            case 'AIRFLOW':
                return check_airflow()
            case 'REDIS_PHEWAS':
                return check_phewas_proxy()
            case 'LOGSTASH':
                return check_logging(n_logs_past_hour)
            case _:
                return check_all(n_logs_past_hour, n_datasets)


def check_all(n_logs_past_hour, n_datasets):
    return {
        '_NOTES_1': "Check uptime and maintenance information at https://status.opengwas.io",
        '_NOTES_2': "Throttling: Please note this endpoint (/api/status) is also subject to throttling (but separate from your API allowance). Do not call this endpoint more often than necessary.",
        '_NOTES_3': "REFERENCES__ASSOCIATIONS_POS_PREFIX_INDICES is a pilot component and its unavailability has no effect on the current API.",
        '_NOTES_4': "STATISTICS__N_REQS_IN_PAST_HOUR is the number of requests processed (not just received) in the past hour. Non-zero number usually means OpenGWAS has been operational overall.",
        'API__VERSION': Globals.VERSION,
        'REFERENCES__ASSOCIATIONS_POS_PREFIX_INDICES': check_gwas_pos_prefix_indices(n_datasets),
        # 'REFERENCES__LD_REF_PANEL': check_ld_ref(),
        # 'REFERENCES__1000_GENOMES_VCF': check_1000g_vcf(),
        'REFERENCES__PLINK': check_plink(),
        'SERVICES__METADATA': Neo4j.check_running(),
        'SERVICES__ASSOCIATIONS': check_elastic(),
        'SERVICES__PHEWAS': check_phewas_proxy(),
        'SERVICES__LOGGING': check_logging(n_logs_past_hour),
        'SERVICES__PIPELINE': check_airflow(),
        'STATISTICS__N_RECORDS': count_elastic_records(),
        'STATISTICS__N_DATASETS': n_datasets,
        'STATISTICS__N_PUBLIC_DATASETS': count_cache_datasets(),
        'STATISTICS__N_REQS_IN_PAST_HOUR': n_logs_past_hour
    }


def check_gwas_pos_prefix_indices(n_datasets):
    if len(Globals.gwas_pos_prefix_indices) == n_datasets:
        return "Available"
    return "Unavailable"


def check_ld_ref():
    if (os.path.isfile(Globals.LD_REF['EUR'] + ".bed") and
            os.path.isfile(Globals.LD_REF['EUR'] + ".bim") and
            os.path.isfile(Globals.LD_REF['EUR'] + ".fam")):
        return "Available"
    return 'Unavailable'


def check_1000g_vcf():
    if (os.path.isfile(Globals.AFL2['vcf']) and 
            os.path.isfile(Globals.AFL2['tbi']) and 
            os.path.isfile(Globals.AFL2['rsidx']) and 
            os.path.isfile(Globals.AFL2['snplist'])):
        return "Available"
    return 'Unavailable'


def check_plink():
    if os.popen(Globals.PLINK + " --version").read().split("\n")[0] != '':
        return "Available"
    return 'Unavailable'


def check_elastic():
    url = f"http://{Globals.app_config['es']['host']}:{Globals.app_config['es']['port']}/_cluster/health"
    auth = HTTPBasicAuth('elastic', Globals.app_config['es']['password'])

    try:
        status = requests.get(url, auth=auth).json()['status']
        if status in ['green', 'yellow']:
            return "Operational"
    except Exception as e:
        print(e)
    return "Error"


def check_airflow():
    url = f"http://{Globals.app_config['airflow']['host']}:{Globals.app_config['airflow']['port']}/api/v1/health"

    try:
        r = requests.get(url, timeout=15)
        rj = r.json()
        if (r.status_code == 200 and
                rj['metadatabase']['status'] == 'healthy' and
                rj['scheduler']['status'] == 'healthy' and
                rj['triggerer']['status'] == 'healthy'):
            return "Operational"
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
        pass
    return "Error"


def check_phewas_proxy():
    url = f"http://{Globals.app_config['redis']['ieu-ssd-proxy']['host']}:{Globals.app_config['redis']['ieu-ssd-proxy']['port']}"
    auth = HTTPBasicAuth(Globals.app_config['redis']['ieu-ssd-proxy']['basic_auth_username'], Globals.app_config['redis']['ieu-ssd-proxy']['basic_auth_passwd'])

    try:
        r = requests.post(url + '/', auth=auth, timeout=15)
        if r.status_code == 200:
            return "Operational"
        print("PheWAS proxy status code: {}".format(r.status_code))
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
        print("PheWAS proxy timeout or connection error: {}".format(e))
    except Exception as e:
        print("PheWAS proxy error: {}".format(e))
    return "Unavailable"


def count_logs_past_hour():
    url = f"http://{Globals.app_config['es']['host']}:{Globals.app_config['es']['port']}/og-logs-api-uuid-*/_count"
    auth = HTTPBasicAuth(Globals.app_config['es']['username'], Globals.app_config['es']['password'])

    try:
        count = requests.get(url,
                           json={"query": {"bool": {"filter": {"range": {"@timestamp": {"gte": "now-1h"}}}}}},
                           auth=auth
                           ).json()['count']
        if count > 0:
            return count
    except Exception as e:
        print(e)
    return 0


def check_logging(n_logs_past_hour):
    return "Operational" if n_logs_past_hour > 0 else "Unavailable"


def count_elastic_records():
    url = f"http://{Globals.app_config['es']['host']}:{Globals.app_config['es']['port']}/_stats/docs"
    auth = HTTPBasicAuth(Globals.app_config['es']['username'], Globals.app_config['es']['password'])

    try:
        return requests.get(url, auth=auth).json()['_all']['primaries']['docs']['count']
    except Exception as e:
        print(e)
    return None


def count_neo4j_datasets():
    try:
        return Neo4j.get_db().run("MATCH (n:GwasInfo) WHERE EXISTS {MATCH (n:GwasInfo)-[r:DID_QC {data_passed:True}]->(u:User)} RETURN COUNT(n) AS n").single()[0]
    except Exception as e:
        print(e)
    return 0


def count_cache_datasets():
    try:
        return json.loads(OCIObjectStorage().object_storage_download('data', 'gwasinfo.json').data.text)['metadata']['size']
    except Exception as e:
        print(e)
    return 0
