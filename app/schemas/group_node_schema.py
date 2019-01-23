from marshmallow import Schema, fields, post_load
from queries.group_node import Group


class GroupNodeSchema(Schema):
    gid = fields.Int(required=True)
    name = fields.Str(required=True)

    @post_load
    def map_to_obj(self, data):
        return Group(**data)
