from queries.unique_node import UniqueNode
import flask
import pytest

d = dict(uid='testid', propone='prop123', proptwo='prop456')


def test_create_node():
    app = flask.Flask(__name__)
    with app.app_context():
        u1 = UniqueNode(d)

        # create node in graph
        u1.create_node()

        # pull node
        u2 = UniqueNode.get_node(d['uid'])

        # check props are correct
        for k in d:
            assert u2.get(k) == d[k]


def test_delete_node():
    app = flask.Flask(__name__)
    with app.app_context():
        u = UniqueNode(d)
        u.create_node()
        UniqueNode.delete_node(d['uid'])
        with pytest.raises(LookupError):
            UniqueNode.get_node(d['uid'])


def test_check_constraint():
    app = flask.Flask(__name__)
    with app.app_context():
        UniqueNode.set_constraint()
        assert UniqueNode.check_constraint()
        UniqueNode.drop_constraint()
        assert not UniqueNode.check_constraint()
