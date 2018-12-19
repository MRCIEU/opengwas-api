from flask_restplus import Api

from .status import api as status
from .gwasinfo import api as gwasinfo
from ._globals import VERSION

api = Api(version=VERSION, title='Bristol GWAS Datastore', description='A RESTful API for querying thousands of GWAS summary datasets', docExpansion='full')

api.add_namespace(status)
api.add_namespace(gwasinfo)
