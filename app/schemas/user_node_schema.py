from marshmallow import Schema, fields, validate, post_load
from queries.user_node import User


class UserNodeSchema(Schema):
    uid = fields.Str(
        required=True,
        validate=validate.Email(error='Not a valid email address')
    )

    @post_load
    def map_to_obj(self, data):
        return User(**data)
