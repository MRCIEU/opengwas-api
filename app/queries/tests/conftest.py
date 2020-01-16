# content of conftest.py
import pytest
from resources.neo4j import Neo4j
import flask
from queries.group_node import Group
from queries.gwas_info_node import GwasInfo
from queries.user_node import User


@pytest.fixture
def reset_db():
    app = flask.Flask(__name__)
    with app.app_context():
        Neo4j.clear_db()
        Neo4j.drop_all_constraints()
        Group.set_constraint()
        assert Group.check_constraint()
        User.set_constraint()
        assert User.check_constraint()
        GwasInfo.set_constraint()
        assert GwasInfo.check_constraint()
