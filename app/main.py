from flask import Flask, send_from_directory, render_template
from apis import api
from resources.globals import Globals
from resources.neo4j import Neo4j
from apis.status import check_all, count_elastic_records, count_neo4j_datasets


def main():
    app = Flask(__name__, static_folder="static")
    app.add_url_rule('/', 'index', index)

    app.config.SWAGGER_UI_DOC_EXPANSION = 'list'
    app.teardown_appcontext(Neo4j.close_db)
    api.init_app(app)

    app.run(host='0.0.0.0', port=Globals.app_config['flask']['port'])


def index():
    status = check_all()
    elastic_counts = count_elastic_records()
    neo4j_counts = count_neo4j_datasets()
    return render_template('index.html', status=status, elastic_counts=elastic_counts, neo4j_counts=neo4j_counts)


if __name__ == "__main__":
    main()
