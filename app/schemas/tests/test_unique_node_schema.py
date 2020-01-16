from schemas.unique_node_schema import UniqueNodeSchema

d = {
    'uid': 'test',
    'propone': 'prop1',
    'proptwo': 'prop2'
}


def test_schema():
    schema = UniqueNodeSchema()
    schema.load(d)
