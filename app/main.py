from flask import Flask
from flask_restplus import Api, Resource, fields
from resources import api

from resources._globals import app_config
from resources.index import Index
from resources.ld import Clump, LdMatrix
from resources.assoc import Assoc
from resources.phewas import Phewas
from resources.tophits import Tophits


# unicode issues
import sys
reload(sys)
sys.setdefaultencoding('utf8')


app = Flask(__name__)
app.config.SWAGGER_UI_DOC_EXPANSION = 'list'
api.init_app(app)
app.run(host='0.0.0.0', debug=True, port=app_config['flask']['port'])

# api.add_resource(GwasInfo, '/gwasinfo', '/gwasinfo/<string:id>') # GET POST
# api.add_resource(Clump, '/clump') # POST
# api.add_resource(LdMatrix, '/ldmatrix') # POST
# api.add_resource(Assoc, '/assoc', '/assoc/<string:id>/<string:rsid>') # GET POST
# api.add_resource(Phewas, '/phewas', '/phewas/<string:rsid>') # GET
# api.add_resource(Tophits, '/tophits') # POST


