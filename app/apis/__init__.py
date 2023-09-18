from flask_restplus import Api
import os

from .status import api as status
from .gwasinfo import api as gwasinfo
from .gicache import api as gicache
from .assoc import api as assoc
from .phewas import api as phewas
from .tophits import api as tophits
from .quality_control import api as quality_control
from .edit import api as edit
from resources.globals import Globals
from .ld import api as ld
from .variants import api as variants
from .batches import api as batches
from .utilities import api as utilities

api = Api(version=Globals.VERSION, title='IEU OpenGWAS database',
          description='A RESTful API for querying thousands of GWAS summary datasets', docExpansion='full',
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

# private
if Globals.app_config['access'] == 'private':
    api.add_namespace(quality_control)
    api.add_namespace(edit)
    api.add_namespace(gicache)
    if os.environ.get('ENV') == 'local':
        api.add_namespace(utilities)
