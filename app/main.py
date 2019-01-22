from flask import Flask
from apis import api
from resources._globals import app_config
from resources._neo4j import close_db


def main():
    app = Flask(__name__)

    app.config.SWAGGER_UI_DOC_EXPANSION = 'list'
    app.teardown_appcontext(close_db)
    api.init_app(app)

    app.run(host='0.0.0.0', debug=True, port=app_config['flask']['port'])


if __name__ == "__main__":
    main()
