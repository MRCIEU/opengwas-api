from queries.study_node import Study
import flask
import pytest

uid = 'test'
pmid = 1234
year = 2000
filename = 'test.txt'
path = '/some/path'
mr = 0
trait = 'trait'
sample_size = 100
unit = 'ug/ul'
priority = 1
author = 'author'


def test_index():
    app = flask.Flask(__name__)

    with app.app_context():
        if not Study.check_constraint():
            Study.set_constraint()

    assert True


def test_create():
    app = flask.Flask(__name__)

    with app.app_context():
        n = Study(uid, pmid, year, filename, path, mr, trait, sample_size, unit, priority, author)
        n.create()


def test_get():
    app = flask.Flask(__name__)

    with app.app_context():
        n = Study.get(uid)

        assert n.uid == uid
        assert n.pmid == pmid
        assert n.year == year
        assert n.filename == filename
        assert n.path == path
        assert n.mr == mr
        assert n.trait == trait
        assert n.sample_size == sample_size
        assert n.unit == unit
        assert n.priority == priority
        assert n.author == author

        with pytest.raises(LookupError):
            Study.get('not_in_db')


def test_update():
    new_path = '/new/path'
    app = flask.Flask(__name__)

    with app.app_context():
        n = Study.get(uid)
        n.path = new_path
        n.create()

        j = Study.get(uid)
        assert j.path == new_path


def test_delete():
    app = flask.Flask(__name__)

    with app.app_context():
        Study.delete(uid)

        # check exception for deleted nodes
        with pytest.raises(LookupError):
            Study.get(uid)
