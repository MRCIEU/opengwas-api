from schemas.user_node_schema import UserNodeSchema

d = {
    'uid': 'e.xample@bristol.ac.uk',
    'admin': False
}

e = {
    'uid': 'e.xample@bristol.ac.uk'
}

f = {
    'uid': ' E.Xample@bristol.ac.uk  '
}


def test_schema():
    schema = UserNodeSchema()
    schema.load(d)
    schema.load(e)
    r = schema.load(e)
    assert r['uid'] == "e.xample@bristol.ac.uk"
