from queries.cql_queries import *
import flask
import pytest


def test_get_all_gwas():
    app = flask.Flask(__name__)
    with app.app_context():
        assert len(get_all_gwas_for_user('NULL')) > 7900
        assert len(get_all_gwas_for_user('g.hemani@bristol.ac.uk')) > 7900


def test_get_all_gwas_ids():
    app = flask.Flask(__name__)
    with app.app_context():
        assert len(get_all_gwas_ids_for_user('NULL')) > 7900


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
        assert get_gwas_for_user('NULL', '300')["id"] == '300'
        print('study_info_chl', study_info(['2']))
        with pytest.raises(LookupError):
            get_gwas_for_user('NULL', '2456766435')
        with pytest.raises(LookupError):
            get_gwas_for_user('NULL', '1128')


def test_check_user_is_admin():
    app = flask.Flask(__name__)
    with app.app_context():
        u = User.get_node("ml18692@bristol.ac.uk")


def test_add_new_gwas_info():
    d = {'pmid': 1234, 'year': 2013,
         'filename': 'test.tab',
         'path': '/test/test', 'mr': 1,
         'note': 'Test',
         'trait': 'Hip circumference', 'category': 'Risk factor', 'subcategory': 'Anthropometric',
         'population': 'European',
         'sex': 'Males', 'ncase': None, 'ncontrol': None, 'sample_size': 60586, 'nsnp': 2725796, 'unit': 'SD (cm)',
         'sd': 8.4548, 'priority': 15, 'author': 'Randall JC', 'consortium': 'GIANT'}

    app = flask.Flask(__name__)
    with app.app_context():
        # check returns id
        uid = add_new_gwas('g.hemani@bristol.ac.uk', d)
        print(uid)
        assert int(uid) > 0

        # TODO now returns string

        # TODO check new gwas requires qc

        # TODO complete qc

        # check in graph query of qc passing
        found = get_gwas_for_user('NULL', uid)
        for k in d:
            if d[k] is None:
                continue
            assert found[k] == d[k]

        # delete
        delete_gwas('g.hemani@bristol.ac.uk', uid)

        # check not in graph
        with pytest.raises(LookupError):
            get_gwas_for_user('NULL', uid)
