from queries.cql_queries import *
import flask
import pytest
from marshmallow.exceptions import ValidationError


def test_add_new_user():
    app = flask.Flask(__name__)
    with app.app_context():
        g = Group(name='public-test')
        g.create_node()

        # should work
        add_new_user('test@email.ac.uk', {'public-test'})
        User.get_node('test@email.ac.uk')
        User.delete_node('test@email.ac.uk')

        # check email formatting
        add_new_user('   Test1@email.ac.uk', {'public-test'})
        User.get_node('test1@email.ac.uk')
        User.delete_node('test1@email.ac.uk')

        # test not email
        with pytest.raises(ValidationError):
            add_new_user('test12344', {'public-test'})

        Group.delete_node('public-test')


def test_add_group_to_user():
    app = flask.Flask(__name__)

    with app.app_context():
        email = 'test2@email.ac.uk'
        group_name = 'pytest'

        g = Group(name='public')
        g.create_node()

        add_new_user(email)

        g = Group(name=group_name)
        g.create_node()

        add_group_to_user(email, group_name)
        grps = get_groups_for_user(email)

        assert group_name in grps
        assert 'public' in grps

        MemberOfRel.delete_rel(User.get_node(email), g)
        Group.delete_node(group_name)
        Group.delete_node('public')
        User.delete_node(email)


def test_get_groups_for_user():
    app = flask.Flask(__name__)
    with app.app_context():
        assert len(get_groups_for_user(None)) == 1


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
        u = User(uid="test@test.ac.uk")
        u.create_node()

        g = Group(name="public")
        g.create_node()

        # check returns id
        uid = add_new_gwas(u['uid'], d)
        assert int(uid.replace('bgc-', '')) > 0

        # check new gwas requires qc
        todos = set()
        for todo in get_todo_quality_control():
            todos.add(todo['id'])
        assert uid in todos

        # complete qc
        add_quality_control(u['uid'], uid, True)

        # check gwas not need qc
        todos = set()
        for todo in get_todo_quality_control():
            todos.add(todo['id'])
        assert uid not in todos

        # check in graph query of qc passing
        found = get_gwas_for_user(None, uid)
        for k in d:
            if d[k] is None:
                continue
            assert found[k] == d[k]

        # delete
        delete_gwas(uid)

        # check not in graph
        with pytest.raises(LookupError):
            get_gwas_for_user(None, uid)
