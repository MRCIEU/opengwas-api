from marshmallow import fields, validate, post_load
from schemas.frpm_schema import FRPMSchema


class UserNodeSchema(FRPMSchema):
    uid = fields.Str(required=True, validate=validate.Email(error='Not a valid email address'),
                     description="Email address of user.")
    admin = fields.Bool(required=False, description="Is the user an admin?")
    first_name = fields.Str(required=True, allow_none=False, validate=validate.Length(min=1, max=40),
                            description="First name")
    last_name = fields.Str(required=True, allow_none=False, validate=validate.Length(min=1, max=40),
                           description="Last name")
    tier = fields.Str(required=True, allow_none=False, validate=validate.OneOf(['ORG', 'PER']), description="Tier of user")
    jwt_timestamp = fields.Int(required=False, description="JWT timestamp")
    created = fields.Int(required=False, description="Timestamp of node creation")
    updated = fields.Int(required=False, description="Timestamp of node update")

    @post_load
    def lower_strip_email(self, item):
        item['uid'] = item['uid'].lower().strip()
        return item
