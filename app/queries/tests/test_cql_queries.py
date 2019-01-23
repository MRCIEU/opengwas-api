from queries.cql_queries import *
import flask


def test_get_all_gwas():
    app = flask.Flask(__name__)
    with app.app_context():
        res = get_all_gwas('g.hemani@bristol.ac.uk')


def test_get_all_gwas_ids():
    app = flask.Flask(__name__)
    with app.app_context():
        get_all_gwas_ids('g.hemani@bristol.ac.uk')
