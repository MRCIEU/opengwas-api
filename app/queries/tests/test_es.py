from queries.es import get_assoc, query_summary_stats
import flask


def test_get_assoc():
    app = flask.Flask(__name__)
    with app.app_context():
        r = get_assoc(None, 'rs4747841', '300', 1, 0.8, 1, 1, 0.3)
        print(r)


def test_query_summary_stats():
    app = flask.Flask(__name__)
    with app.app_context():
        r = query_summary_stats(None, ['rs4747841'], ['300'])
        print(r)
