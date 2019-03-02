from flask import Flask, send_from_directory
from apis import api
from resources._globals import app_config
from resources._neo4j import Neo4j
from werkzeug.contrib.fixers import ProxyFix

app = Flask(__name__, static_folder="reports")
app.wsgi_app = ProxyFix(app.wsgi_app)

app.config.SWAGGER_UI_DOC_EXPANSION = 'list'
app.teardown_appcontext(Neo4j.close_db)
api.init_app(app)


@app.route('/reports/<path:path>')
def send_js(path):
    return send_from_directory('reports', path)


if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=app_config['flask']['port'])
