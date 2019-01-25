from marshmallow import fields, validate
from schemas.frpm_schema import FRPMSchema


class UserNodeSchema(FRPMSchema):
    uid = fields.Str(
        required=True,
        validate=validate.Email(error='Not a valid email address')
    )