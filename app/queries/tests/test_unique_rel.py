from queries.unique_rel import UniqueRel
from queries.unique_node import UniqueNode
import flask
import pytest

d = dict(test_prop1="test_val1", test_prop2="test_val2")


def test_create_rel():
    app = flask.Flask(__name__)
    with app.app_context():
        u1 = UniqueNode(uid='testid1')
        u2 = UniqueNode(uid='testid2')

        # create nodes in graph
        u1.create_node()
        u2.create_node()

        # create rel
        r1 = UniqueRel(**d)
        r1.create_rel(u1, u2)

        # check rel created
        props = UniqueRel.get_rel_props(u1, u2)
        assert props['test_prop1'] == "test_val1"
        assert props['test_prop2'] == "test_val2"


def test_del_rel():
    app = flask.Flask(__name__)
    with app.app_context():
        u1 = UniqueNode(uid='testid1')
        u2 = UniqueNode(uid='testid2')

        # create nodes in graph
        u1.create_node()
        u2.create_node()

        # delete rel
        UniqueRel.delete_rel(u1, u2)

        # check rel deleted
        with pytest.raises(LookupError):
            UniqueRel.get_rel_props(u1, u2)
