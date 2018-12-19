from flask import Flask
from flask_restplus import Api, Resource, fields
from resources import api
from resources._globals import app_config


# unicode issues
import sys
reload(sys)
sys.setdefaultencoding('utf8')


app = Flask(__name__)
app.config.SWAGGER_UI_DOC_EXPANSION = 'list'
api.init_app(app)
app.run(host='0.0.0.0', debug=True, port=app_config['flask']['port'])

