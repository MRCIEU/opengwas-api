from queries.user_node_queries import *
import flask
import pytest

record = {'uid': 'e.xample@bristol.ac.uk'}
app = flask.Flask(__name__)


def test_add_user():
    with app.app_context():
        add_user(record['uid'])
        res = get_user(record['uid'])

        assert res['uid'] == record['uid']


def test_delete_user():
    with app.app_context():
        delete_user(record['uid'])

        with pytest.raises(LookupError):
            get_user(record['uid'])
