from queries.cql_queries import *
import flask
import pytest
from marshmallow.exceptions import ValidationError

gwas_info = {'pmid': 1234, 'year': 2013, 'mr': 1,
             'note': 'Test',
             'trait': 'Hip circumference', 'category': 'Risk factor', 'subcategory': 'Anthropometric',
             'population': 'European',
             'sex': 'Males', 'ncase': None, 'ncontrol': None, 'sample_size': 60586, 'nsnp': 2725796, 'unit': 'SD (cm)',
             'sd': 8.4548, 'priority': 15, 'author': 'Randall JC', 'consortium': 'GIANT'}
email = "test@test.co.uk"
group_name = 'public'


def test_add_new_user(reset_db):
    app = flask.Flask(__name__)
    with app.app_context():
        g = Group(name=group_name)
        g.create_node()

        # should work
        add_new_user(email, {group_name})
        User.get_node(email)

        # check email formatting
        add_new_user('   Test1@email.ac.uk', {'public'})
        User.get_node('test1@email.ac.uk')

        # test not email
        with pytest.raises(ValidationError):
            add_new_user('test12344', {'public'})


def test_add_group_to_user(reset_db):
    app = flask.Flask(__name__)

    with app.app_context():
        second_grp = "developer"

        g = Group(name=group_name)
        g.create_node()

        assert get_groups_for_user(None) == {"public"}

        add_new_user(email)

        g = Group(name=second_grp)
        g.create_node()

        add_group_to_user(email, second_grp)
        grps = get_groups_for_user(email)

        assert group_name in grps
        assert second_grp in grps


def test_add_new_gwas_info(reset_db):
    app = flask.Flask(__name__)
    with app.app_context():
        u = User(uid=email)
        u.create_node()

        g = Group(name=group_name)
        g.create_node()

        # check returns id
        uid = add_new_gwas(email, gwas_info)
        assert int(uid.replace('igd-', '')) > 0

        # check new gwas requires qc
        todos = set()
        for todo in get_todo_quality_control():
            todos.add(todo['id'])
        assert uid in todos

        # complete qc
        add_quality_control(email, uid, True)

        # check gwas not need qc
        todos = set()
        for todo in get_todo_quality_control():
            todos.add(todo['id'])
        assert uid not in todos

        # check in graph query of qc passing
        found = get_gwas_for_user(None, uid)
        for k in gwas_info:
            if gwas_info[k] is None:
                continue
            assert found[k] == gwas_info[k]

        # delete
        delete_gwas(uid)

        # check not in graph
        with pytest.raises(LookupError):
            get_gwas_for_user(None, uid)


def test_get_permitted_studies(reset_db):
    app = flask.Flask(__name__)
    with app.app_context():
        g = Group(name=group_name)
        g.create_node()

        add_new_user(email)

        uid = add_new_gwas(email, gwas_info)
        add_quality_control(email, uid, True)

        assert len(get_permitted_studies(email, [uid])) == 1
