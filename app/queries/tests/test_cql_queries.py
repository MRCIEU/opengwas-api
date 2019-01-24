from queries.cql_queries import *
import flask
import pytest


def test_get_all_gwas():
    app = flask.Flask(__name__)
    with app.app_context():
        assert len(get_all_gwas('NULL')) > 7900
        assert len(get_all_gwas('g.hemani@bristol.ac.uk')) > 7900


def test_get_all_gwas_ids():
    app = flask.Flask(__name__)
    with app.app_context():
        assert len(get_all_gwas_ids('NULL')) > 7900


def test_get_groups_for_user():
    app = flask.Flask(__name__)
    with app.app_context():
        assert len(get_groups_for_user('NULL')) == 1
        assert len(get_groups_for_user('g.hemani@bristol.ac.uk')) > 1


def test_study_info():
    app = flask.Flask(__name__)
    with app.app_context():
        assert len(study_info('snp_lookup')) > 7900
        assert len(study_info([300])) == 1
        assert len(study_info(['300'])) == 1


def test_get_specific_gwas():
    app = flask.Flask(__name__)
    with app.app_context():
        assert get_specific_gwas('NULL', '300')["id"] == '300'
        with pytest.raises(LookupError):
            get_specific_gwas('NULL', '2456766435')
        with pytest.raises(LookupError):
            get_specific_gwas('NULL', '1128')
