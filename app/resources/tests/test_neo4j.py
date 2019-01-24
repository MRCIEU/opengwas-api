from resources._neo4j import Neo4j
import flask


def test_check_running():
    app = flask.Flask(__name__)
    with app.app_context():
        assert Neo4j.check_running()
