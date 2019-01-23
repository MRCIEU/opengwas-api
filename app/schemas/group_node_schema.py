from marshmallow import fields, post_load
from schemas.frpm_schema import FRPMSchema
from queries.group_node import Group


class GroupNodeSchema(FRPMSchema):
    gid = fields.Int(required=True)
    name = fields.Str(required=True)

    @post_load
    def map_to_obj(self, data):
        return Group(**data)
