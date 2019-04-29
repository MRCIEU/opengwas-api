from marshmallow import fields
from schemas.frpm_schema import FRPMSchema


class GroupNodeSchema(FRPMSchema):
    name = fields.Str(required=True, description="Group name")
