from flask import Blueprint
from flask_restx import Api
import os

from resources.globals import Globals
from werkzeug.exceptions import TooManyRequests

from .index import index
from .status import api as status
from .batches import api as batches
from .user import api as user

from .gwasinfo import api as gwasinfo
from .gicache import api as gicache
from .assoc import api as assoc
from .tophits import api as tophits
from .phewas import api as phewas
from .variants import api as variants
from .ld import api as ld

from .stats import api as stats
from .quality_control import api as quality_control
from .edit import api as edit
from .utilities import api as utilities

api_bp = Blueprint('api', __name__)
# https://stackoverflow.com/a/56540031
api_bp.add_url_rule('/', view_func=index)
api = Api(api_bp, version=Globals.VERSION, title='IEU OpenGWAS database',
          description='A RESTful API for querying tens of thousands of GWAS summary datasets', docExpansion='full',
          doc='/docs', authorizations={
              'token_jwt': {
                  'type': 'apiKey',
                  'in': 'header',
                  'name': 'Authorization',
                  'description': 'Prepend "<code>Bearer(whitespace)</code>" to your token. The entire value provided for this header should be like: <code>Bearer ey******.**********.*********</code>. Read more at https://api.opengwas.io/api/#authentication'
              }
          }, security=['token_jwt'])

# public
api.add_namespace(status)
api.add_namespace(batches)
api.add_namespace(user)
api.add_namespace(gwasinfo)
api.add_namespace(assoc)
api.add_namespace(tophits)
api.add_namespace(phewas)
api.add_namespace(variants)
api.add_namespace(ld)
api.add_namespace(edit)
api.add_namespace(quality_control)
api.add_namespace(stats)

# private
if Globals.app_config['access'] == 'private':
    api.add_namespace(gicache)

if os.environ.get('ENV') == 'local':
    api.add_namespace(utilities)


@api.errorhandler(TooManyRequests)
def handle_429(e):
    return e.response.json, 429
