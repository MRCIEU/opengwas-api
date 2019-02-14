from marshmallow import fields, validate
from schemas.frpm_schema import FRPMSchema


class UserNodeSchema(FRPMSchema):
    uid = fields.Str(required=False, validate=validate.Email(error='Not a valid email address'),
                     description="Email address of user.")
    admin = fields.Bool(required=False, description="Is the user an admin?")
