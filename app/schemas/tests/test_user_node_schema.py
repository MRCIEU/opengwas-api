from schemas.user_node_schema import UserNodeSchema

d = {
    'uid': 'e.xample@bristol.ac.uk'
}


def test_schema():
    schema = UserNodeSchema()
    schema.load(d)
