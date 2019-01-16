from flask_restplus import Namespace, Resource
from resources._globals import *
from resources._logger import *
import requests

api = Namespace('status', description="Status of API and linked resources")


@api.route('/')
@api.doc(description="Something something something")
class Status(Resource):
    def get(self):
        logger_info()
        out = {
            'API version': VERSION,
            'Neo4j status': check_neo4j(),
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


def check_elastic():
    url = 'http://' + app_config['es']['host'] + ':' + str(app_config['es']['port']) + '/_cluster/health?pretty'
    try:
        out = requests.get(url).json()
        if out['status'] == 'red':
            return "Unavailable"
        else:
            return "Available"
    except Exception as e:
        print(e)
        return "Error"


def check_neo4j():
    # TODO
    pass
