from marshmallow import Schema
from flask_restplus import fields

""" Schema class compatible with Flask-restplus """


class FRPMSchema(Schema):
    @classmethod
    def get_flask_model(cls):
        schema_fields = vars(cls)['_declared_fields']
        model = dict()

        for prop in schema_fields:
            s = str(prop)
            p = str(type(schema_fields[prop]).__name__)

            if p == 'Integer':
                model[s] = fields.Integer
            elif p == 'String':
                model[s] = fields.String
            elif p == 'Float':
                model[s] = fields.Float
            else:
                raise LookupError("Could not map {}".format(p))

        return model
