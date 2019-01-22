from marshmallow import Schema, fields


class GroupNodeSchema(Schema):
    LABEL = 'Group'

    gid = fields.Int(required=True)
    name = fields.Str(required=True)
