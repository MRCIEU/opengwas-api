from queries.unique_node import UniqueNode
import pytest
import flask

uid = 'uid'


def test_index():
    app = flask.Flask(__name__)

    with app.app_context():
        if not UniqueNode.check_constraint():
            UniqueNode.set_constraint()

    assert True


def test_create():
    app = flask.Flask(__name__)

    with app.app_context():
        n = UniqueNode(uid)
        n.create()


def test_get():
    app = flask.Flask(__name__)

    with app.app_context():
        n = UniqueNode.get(uid)
        assert n.uid == uid


def test_delete():
    app = flask.Flask(__name__)

    with app.app_context():
        UniqueNode.delete(uid)

        with pytest.raises(LookupError):
            UniqueNode.get(uid)
