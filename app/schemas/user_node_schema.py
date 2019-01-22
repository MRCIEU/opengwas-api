from marshmallow import Schema, fields, validate


class UserNodeSchema(Schema):
    LABEL = 'User'

    uid = fields.Str(
        required=True,
        validate=validate.Email(error='Not a valid email address')
    )
