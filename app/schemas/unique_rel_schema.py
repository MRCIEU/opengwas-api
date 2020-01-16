from marshmallow import fields, validate
from schemas.frpm_schema import FRPMSchema


class UniqueRelSchema(FRPMSchema):
    test_prop1 = fields.Str(required=True, allow_none=False)
    test_prop2 = fields.Str(required=True, allow_none=False)
