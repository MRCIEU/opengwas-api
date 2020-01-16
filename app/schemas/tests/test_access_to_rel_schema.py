from schemas.access_to_rel_schema import AccessToRelSchema

d = {}


def test_schema():
    schema = AccessToRelSchema()
    schema.load(d)
