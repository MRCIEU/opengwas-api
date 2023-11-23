from flask import Blueprint
from flask_restx import Api
import os

from resources.globals import Globals
from .index import index
from .status import api as status
from .gwasinfo import api as gwasinfo
from .gicache import api as gicache
from .assoc import api as assoc
from .phewas import api as phewas
from .tophits import api as tophits
from .quality_control import api as quality_control
from .edit import api as edit
from .ld import api as ld
from .variants import api as variants
from .batches import api as batches
from .utilities import api as utilities

api_bp = Blueprint('api', __name__)
# https://stackoverflow.com/a/56540031
api_bp.add_url_rule('/', '/', view_func=index)
api = Api(api_bp, version=Globals.VERSION, title='IEU OpenGWAS database',
          description='A RESTful API for querying tens of thousands of GWAS summary datasets', docExpansion='full',
          doc='/docs/')

# public
api.add_namespace(status)
api.add_namespace(batches)
api.add_namespace(gwasinfo)
api.add_namespace(assoc)
api.add_namespace(tophits)
api.add_namespace(phewas)
api.add_namespace(variants)
api.add_namespace(ld)

if os.environ.get('ENV') == 'local':
    api.add_namespace(utilities)

# private
if Globals.app_config['access'] == 'private':
    api.add_namespace(quality_control)
    api.add_namespace(edit)
    api.add_namespace(gicache)
