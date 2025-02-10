from flask import request
from flask_restx import Namespace, Resource
import requests
from requests.auth import HTTPBasicAuth
import os
import json

from resources.globals import Globals
from resources.neo4j import Neo4j
from resources._oci import OCI
from middleware.limiter import limiter

api = Namespace('status', description="Status of API and linked resources")


@api.route('')
@api.doc(description="Check services are running")
class Status(Resource):
    @api.doc(id='status_get', security=[])
    @limiter.limit('300 per hour')  # Max number of requests per IP
    def get(self):
        n_logs_past_hour = count_logs_past_hour()

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
                return check_all(n_logs_past_hour)


def check_all(n_logs_past_hour):
    return {
        'Uptime and maintenance information': "https://status.opengwas.io",
        '[API] Version': Globals.VERSION,
        '[References] LD reference panel': check_ld_ref(),
        '[References] 1000 genomes annotation VCF': check_1000g_vcf(),
        '[References] PLINK executable': check_plink(),
        '[Services] Metadata': Neo4j.check_running(),
        '[Services] Associations': check_elastic(),
        '[Services] PheWAS': check_phewas_proxy(),
        '[Services] Logging': check_logging(n_logs_past_hour),
        '[Services] Pipeline': check_airflow(),
        '[Statistics] N records': count_elastic_records(),
        '[Statistics] N datasets': count_neo4j_datasets(),
        '[Statistics] N public datasets': count_cache_datasets(),
        '[Statistics] N requests processed in the past hour': n_logs_past_hour
    }


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
        return Neo4j.get_db().run("MATCH (n:GwasInfo) return count(n) as n").single()[0]
    except Exception as e:
        print(e)
    return 0


def count_cache_datasets():
    try:
        return json.loads(OCI().object_storage_download('data', 'gwasinfo.json').data.text)['metadata']['size']
    except Exception as e:
        print(e)
    return 0
