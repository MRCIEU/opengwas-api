from queries.cql_queries import get_permitted_studies
import flask


def test_get_permitted_studies():
    app = flask.Flask(__name__)
    with app.app_context():
        assert len(get_permitted_studies(None, ['300'])) == 1
        #assert len(get_permitted_studies('ml18692@bristol.ac.uk', ['300'])) == 1
