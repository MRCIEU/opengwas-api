from marshmallow import fields, post_load
from schemas.frpm_schema import FRPMSchema


class GroupNodeSchema(FRPMSchema):
    gid = fields.Int(required=True)
    name = fields.Str(required=True)
