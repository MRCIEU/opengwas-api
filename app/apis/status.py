from flask import g
from flask_restplus import Namespace, Resource
from resources._globals import *
from resources._logger import *
from resources._neo4j import Neo4j
import requests

api = Namespace('status', description="Status of API and linked resources")


@api.route('')
@api.doc(description="Check services are running")
class Status(Resource):
    def get(self):
        print(str(count_elastic_calls()))
        logger_info()
        return check_all()


def check_all():
    out = {
        'API version': VERSION,
        'Access': app_config['access'],
        'Neo4j status': Neo4j.check_running(),
        'ElasticSearch status': check_elastic(),
        'LD reference panel': check_ld_ref(),
        'PLINK executable': check_plink()
    }
    return out

def check_ld_ref():
    if (os.path.isfile(LD_REF + ".bed") and os.path.isfile(LD_REF + ".bim") and os.path.isfile(LD_REF + ".fam")):
        return "Available"
    else:
        return 'Unavailable'


def check_plink():
    if os.popen(PLINK + " --version").read().split("\n")[0] == '':
        return 'Unavailable'
    else:
        return "Available"


def count_elastic_records():
    url = 'http://' + app_config['es']['host'] + ':' + str(app_config['es']['port']) + '/_stats/docs'
    try:
        out = requests.get(url).json()['_all']['primaries']['docs']['count']
        print(out)
        return out
    except Exception as e:
        return None


# TODO: This doesn't work
# curl -XPOST 'localhost:9200/logstash*/_search' -H 'Content-Type: application/json' -d '{"_source":"/var/www/api/mr-base-api/app/logs/mrbaseapi.log","size":0, "query": { "bool": {"filter": { "range": { "@timestamp": {"gte": "now-30d", "lte": "now"}}}}}, "aggs" : {"api-calls" : {"date_histogram" : {"field" : "@timestamp","interval" : "day"}}}}' | jq '.aggregations."api-calls".buckets'
def count_elastic_calls(epoch='30d'):
    url = 'http://' + app_config['es']['host'] + ':' + str(app_config['es']['port']) + "/logstash*/_search"

    payload = {"_source":"/var/www/api/mr-base-api/app/logs/mrbaseapi.log","size":0, "query": { "bool": {"filter": { "range": { "@timestamp": {"gte": "now-"+epoch, "lte": "now"}}}}}, "aggs" : {"api-calls" : {"date_histogram" : {"field" : "@timestamp","interval" : "day"}}}}
    r = requests.post(url, data=payload, headers={"Content-Type": "application/json"})
    print(r.json())
    return(r)


def count_neo4j_datasets():
    try:
        tx = Neo4j.get_db()
        res = tx.run("MATCH (n:GwasInfo) return count(n) as n").single()[0]
        return(res)
    except Exception as e:
        return None


def check_elastic():
    url = 'http://' + app_config['es']['host'] + ':' + str(app_config['es']['port']) + '/_cluster/health?pretty'
    count_elastic_records()
    try:
        out = requests.get(url).json()
        if out['status'] == 'red':
            return "Unavailable"
        else:
            return "Available"
    except Exception as e:
        return "Error"


