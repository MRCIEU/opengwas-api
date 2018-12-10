import sys
from flask import Flask
from flask_restful import Api
from resources._globals import app_config
from resources.index import Index
from resources.status import Status
from resources.gwasinfo import GwasInfo
from resources.ld import Clump, LdMatrix
from resources.assoc import Assoc
from resources.phewas import Phewas
from resources.tophits import Tophits


#unicode issues
reload(sys)
sys.setdefaultencoding('utf8')


app = Flask(__name__)
api = Api(app)


api.add_resource(Index, '/') # GET
api.add_resource(Status, '/status') # GET
api.add_resource(GwasInfo, '/gwasinfo', '/gwasinfo/<string:id>') # GET POST
api.add_resource(Clump, '/clump') # POST
api.add_resource(LdMatrix, '/ldmatrix') # POST
api.add_resource(Assoc, '/assoc', '/assoc/<string:id>/<string:rsid>') # GET POST
api.add_resource(Phewas, '/phewas', '/phewas/<string:rsid>') # GET
api.add_resource(Tophits, '/tophits') # POST


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=app_config['flask']['port'])

