from flask_restx import Namespace, Resource
import requests
from requests.auth import HTTPBasicAuth
import os
import json

from resources.globals import Globals
from resources.neo4j import Neo4j
# from resources.cromwell import Cromwell
from middleware.limiter import limiter

api = Namespace('status', description="Status of API and linked resources")


@api.route('')
@api.doc(description="Check services are running")
class Status(Resource):
    @api.doc(id='status_get', security=[])
    @limiter.limit('300 per hour')  # Max number of requests per IP
    def get(self):
        # print(str(count_elastic_calls()))
        return check_all()


def check_all():
    out = {
        'API version': Globals.VERSION,
        'Access': Globals.app_config['access'],
        'Neo4j': Neo4j.check_running(),
        'ElasticSearch': check_elastic(),
        'Airflow': check_airflow(),
        'PheWAS': check_phewas_fast(),
        'LD reference panel': check_ld_ref(),
        '1000 genomes annotation VCF': check_1000g_vcf(),
        'PLINK executable': check_plink(),
        # 'Cromwell': check_cromwell(),
        'Total associations': count_elastic_records(),
        'Total complete datasets': count_neo4j_datasets(),
        'Total public datasets': count_cache_datasets()
        # 'API queries this month': count_elastic_calls()
    }
    return out


def check_ld_ref():
    if (os.path.isfile(Globals.LD_REF['EUR'] + ".bed") and os.path.isfile(Globals.LD_REF['EUR'] + ".bim") and os.path.isfile(
            Globals.LD_REF['EUR'] + ".fam")):
        return "Available"
    else:
        return 'Unavailable'


def check_1000g_vcf():
    if (os.path.isfile(Globals.AFL2['vcf']) and os.path.isfile(Globals.AFL2['tbi']) and os.path.isfile(Globals.AFL2['rsidx']) and os.path.isfile(Globals.AFL2['snplist'])):
        return "Available"
    else:
        return 'Unavailable'


def check_plink():
    if os.popen(Globals.PLINK + " --version").read().split("\n")[0] == '':
        return 'Unavailable'
    else:
        return "Available"


def count_elastic_records():
    url = Globals.app_config['es']['scheme'] + "://" + Globals.app_config['es']['host'] + ':' + str(Globals.app_config['es']['port']) + '/_stats/docs'
    try:
        out = requests.get(url, auth=HTTPBasicAuth('elastic', Globals.app_config['es']['password'])).json()['_all']['primaries']['docs']['count']
        return out
    except Exception as e:
        return None


# TODO: This doesn't work
# curl -XPOST 'localhost:9200/logstash*/_search' -H 'Content-Type: application/json' -d '{"_source":"/var/www/api/mr-base-api/app/logs/mrbaseapi.log","size":0, "query": { "bool": {"filter": { "range": { "@timestamp": {"gte": "now-30d", "lte": "now"}}}}}, "aggs" : {"api-calls" : {"date_histogram" : {"field" : "@timestamp","interval" : "day"}}}}' | jq '.aggregations."api-calls".buckets'
def count_elastic_calls(epoch='30d'):
    url = Globals.app_config['es']['scheme'] + "://" + Globals.app_config['es']['host'] + ':' + str(
        Globals.app_config['es']['port']) + "/logstash*/_search"

    payload = {"_source": "/var/www/api/mr-base-api/app/logs/mrbaseapi.log", "size": 0,
               "query": {"bool": {"filter": {"range": {"@timestamp": {"gte": "now-" + epoch, "lte": "now"}}}}},
               "aggs": {"api-calls": {"date_histogram": {"field": "@timestamp", "interval": "day"}}}}
    r = requests.post(url, data=payload, headers={"Content-Type": "application/json"}, auth=HTTPBasicAuth('elastic', Globals.app_config['es']['password']))
    return (r)


def count_neo4j_datasets():
    try:
        tx = Neo4j.get_db()
        res = tx.run("MATCH (n:GwasInfo) return count(n) as n").single()[0]
        return (res)
    except Exception as e:
        return None


def count_cache_datasets():
    try:
        with open(Globals.STATIC_GWASINFO, 'r') as f:
            gi = json.load(f)
        return (len(gi))
    except Exception as e:
        return None


def check_elastic():
    url = Globals.app_config['es']['scheme'] + "://" + Globals.app_config['es']['host'] + ':' + str(
        Globals.app_config['es']['port']) + '/_cluster/health?pretty'
    count_elastic_records()
    try:
        out = requests.get(url, auth=HTTPBasicAuth('elastic', Globals.app_config['es']['password'])).json()
        if out['status'] == 'red':
            return "Unavailable"
        else:
            return "Available"
    except Exception as e:
        return "Error"


def check_cromwell():
    try:
        r = requests.get(Globals.CROMWELL_URL + '/engine/v1/version', auth=Globals.CROMWELL_AUTH, timeout=15)
        if r.status_code == 200:
            return "Available"
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
        pass
    return "Unavailable"


def check_airflow():
    url = 'http://' + Globals.app_config['airflow']['host'] + ':' + str(Globals.app_config['airflow']['port']) + '/api/v1/health'

    try:
        r = requests.get(url, timeout=15)
        rj = r.json()
        if r.status_code == 200 and rj['metadatabase']['status'] == 'healthy' and rj['scheduler']['status'] == 'healthy' and rj['triggerer']['status'] == 'healthy':
            return "Available"
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
        pass
    return "Unavailable"


def check_phewas_fast():
    url = 'http://' + Globals.app_config['redis']['ieu-ssd-proxy']['host'] + ":" + str(Globals.app_config['redis']['ieu-ssd-proxy']['port'])
    auth = requests.auth.HTTPBasicAuth(Globals.app_config['redis']['ieu-ssd-proxy']['basic_auth_username'], Globals.app_config['redis']['ieu-ssd-proxy']['basic_auth_passwd'])

    try:
        r = requests.post(url + '/', auth=auth, timeout=15)
        if r.status_code == 200:
            return "Available"
        else:
            print("PheWAS proxy status code: {}".format(r.status_code))
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
        print("PheWAS proxy error: {}".format(e))
    except Exception as e:
        print("PheWAS proxy error: {}".format(e))
    return "Unavailable"
