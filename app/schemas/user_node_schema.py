from marshmallow import fields, validate, post_load
from schemas.frpm_schema import FRPMSchema


class UserNodeSchema(FRPMSchema):
    uid = fields.Str(required=True, validate=validate.Email(error='Not a valid email address'),
                     metadata={"description": "Email address of user."})
    admin = fields.Bool(required=False, metadata={"description": "Is the user an admin?"})
    role = fields.Str(required=False, validate=validate.OneOf(['admin']), metadata={"description": "Role of user"})
    first_name = fields.Str(required=True, allow_none=False, validate=validate.Length(min=1, max=40),
                            metadata={"description": "First name"})
    last_name = fields.Str(required=True, allow_none=False, validate=validate.Length(min=1, max=40),
                           metadata={"description": "Last name"})
    tier = fields.Str(required=True, allow_none=False, validate=validate.OneOf(['ORG', 'PER']), metadata={"description": "Tier of user"})
    source = fields.Str(required=True, allow_none=False, validate=validate.OneOf(['MS', 'GH', 'EM']), metadata={"description": "Source of user info"})
    jwt_timestamp = fields.Int(required=False, metadata={"description": "JWT timestamp"})
    created = fields.Int(required=False, metadata={"description": "Timestamp of node creation"})
    updated = fields.Int(required=False, metadata={"description": "Timestamp of node update"})

    @post_load
    def lower_strip_email(self, item, **kwargs):
        item['uid'] = item['uid'].lower().strip()
        return item
