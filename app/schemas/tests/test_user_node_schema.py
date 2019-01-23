from schemas.user_node_schema import UserNodeSchema

d = {
    'uid': 'e.xample@bristol.ac.uk'
}


def test_schema():
    UserNodeSchema().load(d)
