from marshmallow import Schema, fields, post_load


class UniqueNodeSchema(Schema):
    uid = fields.Str()
    email = fields.Email()
    created_at = fields.DateTime()

    @post_load
    def make_user(self, data):
        return User(**data)
