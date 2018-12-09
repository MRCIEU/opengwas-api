import sys
from flask import Flask
from flask_restful import Api
from resources._globals import es_conf
from resources.index import Index
from resources.status import Status
from resources.gwasinfo import GwasList, GwasInfo, GwasListAuth
from resources.ld import Clump, LdMatrix
from resources.assoc import AssocGet, AssocPost


#unicode issues
reload(sys)
sys.setdefaultencoding('utf8')


app = Flask(__name__)
api = Api(app)


api.add_resource(Index, '/')
api.add_resource(Status, '/status')
api.add_resource(GwasList, '/gwaslist')
api.add_resource(GwasListAuth, '/gwaslist/<string:token>')
api.add_resource(GwasInfo, '/gwasinfo/<string:id>')
api.add_resource(Clump, '/clump')
api.add_resource(LdMatrix, '/ldmatrix')
api.add_resource(AssocGet, '/assoc/<string:id>/<string:rsid>')
api.add_resource(AssocPost, '/assoc')


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=es_conf['flask_port'])

