from marshmallow import fields, post_load
from queries.unique_node import UniqueNode
from schemas.frpm_schema import FRPMSchema


class UniqueNodeSchema(FRPMSchema):
    uid = fields.Str(required=True, allow_none=False)
    propone = fields.Str(required=True, allow_none=False)
    proptwo = fields.Str(required=True, allow_none=False)

    @post_load
    def map_to_obj(self, data):
        return UniqueNode(**data)
