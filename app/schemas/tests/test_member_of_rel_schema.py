from schemas.member_of_rel_schema import MemberOfRelSchema

d = {}


def test_schema():
    schema = MemberOfRelSchema()
    schema.load(d)
