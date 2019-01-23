from marshmallow import fields, validate, post_load
from queries.user_node import User
from schemas.frpm_schema import FRPMSchema


class UserNodeSchema(FRPMSchema):
    uid = fields.Str(
        required=True,
        validate=validate.Email(error='Not a valid email address')
    )

    @post_load
    def map_to_obj(self, data):
        return User(**data)
