from schemas.group_node_schema import GroupNodeSchema

d = {
    "name": "public",
    "gid": 1
}


def test_schema():
    schema = GroupNodeSchema()
    schema.load(d)
