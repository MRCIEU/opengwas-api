from schemas.unique_rel_schema import UniqueRelSchema

d = {
    'test_prop1': 'test_prop1',
    'test_prop2': 'test_prop2'
}


def test_schema():
    schema = UniqueRelSchema()
    schema.load(d)
