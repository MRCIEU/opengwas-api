from resources.neo4j import Neo4j
import flask


def test_check_running():
    app = flask.Flask(__name__)
    with app.app_context():
        assert Neo4j.check_running() == "Available"


def test_drop_all_index():
    app = flask.Flask(__name__)
    with app.app_context():
        Neo4j.drop_all_constraints()
