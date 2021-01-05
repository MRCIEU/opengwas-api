from flask_restplus import Namespace, Resource
from resources.globals import Globals
from resources.neo4j import Neo4j
from resources.cromwell import Cromwell
import requests
import os
import json

api = Namespace('status', description="Status of API and linked resources")


@api.route('')
@api.doc(description="Check services are running")
class Status(Resource):
    def get(self):
        print(str(count_elastic_calls()))
        return check_all()


def check_all():
    try:
        Cromwell.get_version()
        cromwell_status = 'Available'
    except Exception:
        cromwell_status = 'Unavailable'

    out = {
        'API version': Globals.VERSION,
        'Access': Globals.app_config['access'],
        'Neo4j status': Neo4j.check_running(),
        'ElasticSearch status': check_elastic(),
        'LD reference panel': check_ld_ref(),
        '1000 genomes annotation VCF': check_1000g_vcf(),
        'PLINK executable': check_plink(),
        'Cromwell': cromwell_status,
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
    url = 'http://' + Globals.app_config['es']['host'] + ':' + str(Globals.app_config['es']['port']) + '/_stats/docs'
    try:
        out = requests.get(url).json()['_all']['primaries']['docs']['count']
        return out
    except Exception as e:
        return None

# TODO: This doesn't work
# curl -XPOST 'localhost:9200/logstash*/_search' -H 'Content-Type: application/json' -d '{"_source":"/var/www/api/mr-base-api/app/logs/mrbaseapi.log","size":0, "query": { "bool": {"filter": { "range": { "@timestamp": {"gte": "now-30d", "lte": "now"}}}}}, "aggs" : {"api-calls" : {"date_histogram" : {"field" : "@timestamp","interval" : "day"}}}}' | jq '.aggregations."api-calls".buckets'
def count_elastic_calls(epoch='30d'):
    url = 'http://' + Globals.app_config['es']['host'] + ':' + str(
        Globals.app_config['es']['port']) + "/logstash*/_search"

    payload = {"_source": "/var/www/api/mr-base-api/app/logs/mrbaseapi.log", "size": 0,
               "query": {"bool": {"filter": {"range": {"@timestamp": {"gte": "now-" + epoch, "lte": "now"}}}}},
               "aggs": {"api-calls": {"date_histogram": {"field": "@timestamp", "interval": "day"}}}}
    r = requests.post(url, data=payload, headers={"Content-Type": "application/json"})
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
    url = 'http://' + Globals.app_config['es']['host'] + ':' + str(
        Globals.app_config['es']['port']) + '/_cluster/health?pretty'
    count_elastic_records()
    try:
        out = requests.get(url).json()
        if out['status'] == 'red':
            return "Unavailable"
        else:
            return "Available"
    except Exception as e:
        return "Error"
