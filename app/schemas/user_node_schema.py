from marshmallow import fields, validate, post_load
from schemas.frpm_schema import FRPMSchema


class UserNodeSchema(FRPMSchema):
    uid = fields.Str(required=True, validate=validate.Email(error='Not a valid email address'),
                     metadata={"description": "Email address of user"})
    role = fields.List(fields.Str(validate=validate.OneOf(['admin', 'contributor'])), required=False, metadata={"description": "Roles of user"})
    first_name = fields.Str(required=True, allow_none=False, validate=validate.Length(min=1, max=40),
                            metadata={"description": "First name"})
    last_name = fields.Str(required=True, allow_none=False, validate=validate.Length(min=1, max=40),
                           metadata={"description": "Last name"})
    group = fields.Str(required=True, allow_none=False, validate=validate.OneOf(['ORG', 'PER']), metadata={"description": "Group of user"})
    source = fields.Str(required=True, allow_none=False, validate=validate.OneOf(['MS', 'GH', 'EM']), metadata={"description": "Method of last sign-in"})
    jwt_timestamp = fields.Int(required=False, metadata={"description": "JWT timestamp"})
    created = fields.Int(required=False, metadata={"description": "Timestamp of node creation"})
    last_signin = fields.Int(required=False, metadata={"description": "Timestamp of most recent sign-in"})
    uuid = fields.Str(required=False, metadata={"description": "Shortened UUID of user"})
    is_trial = fields.Boolean(required=False, metadata={"description": "Is this a trial account"})

    @post_load
    def lower_strip_email(self, item, **kwargs):
        item['uid'] = item['uid'].lower().strip()
        return item
