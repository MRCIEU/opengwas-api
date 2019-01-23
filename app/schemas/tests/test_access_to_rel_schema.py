from schemas.access_to_rel_schema import AccessToRelSchema

d = {}


def test_schema():
    AccessToRelSchema().load(d)
