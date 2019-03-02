from flask import Flask, send_from_directory, render_template
from apis import api
from resources._globals import app_config
from resources._neo4j import Neo4j
from apis.status import check_all, count_elastic_records, count_neo4j_datasets

app = Flask(__name__, static_folder="reports")

app.config.SWAGGER_UI_DOC_EXPANSION = 'list'
app.teardown_appcontext(Neo4j.close_db)
api.init_app(app)


@app.route('/reports/<path:path>')
def send_js(path):
    return send_from_directory('reports', path)

@app.route('/about')
def index():
    status = check_all()
    elastic_counts = count_elastic_records()
    neo4j_counts = count_neo4j_datasets()
    return render_template('index.html', status=status, elastic_counts=elastic_counts, neo4j_counts=neo4j_counts)

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=app_config['flask']['port'])
