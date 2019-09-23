from queries.cql_queries import get_permitted_studies
from queries.es import query_summary_stats, get_assoc
import flask


def test_get_permitted_studies():
    app = flask.Flask(__name__)
    with app.app_context():
        assert len(get_permitted_studies(None, ['IEU-a-300'])) == 1
        assert len(get_permitted_studies('ml18692@bristol.ac.uk', ['IEU-a-300'])) == 1


def test_get_assoc():
    app = flask.Flask(__name__)
    with app.app_context():
        assert len(get_assoc(None, ['rs4747841'], ['IEU-a-300'], 1, 0.8, 1, 1, 0.3)) == 1
        assert len(get_assoc('ml18692@bristol.ac.uk', ['rs4747841'], ['IEU-a-300'], 1, 0.8, 1, 1, 0.3)) == 1


def test_query_summary_stats():
    app = flask.Flask(__name__)
    with app.app_context():
        assert len(query_summary_stats(None, ['rs4747841'], ['IEU-a-300'])) == 1
        assert len(query_summary_stats('ml18692@bristol.ac.uk', ['rs4747841'], ['IEU-a-300'])) == 1
        assert len(query_summary_stats('ml18692@bristol.ac.uk', ['rs4747841'], ['IEU-a-300'])) == 1
        assert len(query_summary_stats(None, ['rs4747841'], 'snp_lookup')) > 20000
