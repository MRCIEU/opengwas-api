from queries.es import get_assoc
import flask


def test_get_assoc():
    app = flask.Flask(__name__)
    with app.app_context():
        get_assoc('NULL', 'rs234'.split(','), '2'.split(','), 1, 0.8, 1, 1, 0.3)
        assert True
