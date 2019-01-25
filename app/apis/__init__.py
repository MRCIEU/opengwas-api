from flask_restplus import Api

from .status import api as status
from .gwasinfo import api as gwasinfo
from .assoc import api as assoc
from .phewas import api as phewas
from .tophits import api as tophits
from resources._globals import VERSION
from .ld import api as ld
from .upload_gwas import api as upload

api = Api(version=VERSION, title='Bristol GWAS Datastore',
          description='A RESTful API for querying thousands of GWAS summary datasets', docExpansion='full')

api.add_namespace(status)
api.add_namespace(gwasinfo)
api.add_namespace(assoc)
api.add_namespace(phewas)
api.add_namespace(tophits)
api.add_namespace(ld)
api.add_namespace(upload)
