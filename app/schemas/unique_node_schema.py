from marshmallow import fields
from schemas.frpm_schema import FRPMSchema


class UniqueNodeSchema(FRPMSchema):
    uid = fields.Str(required=True, allow_none=False)
    propone = fields.Str(required=True, allow_none=False)
    proptwo = fields.Str(required=True, allow_none=False)
