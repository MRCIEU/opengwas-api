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

    @classmethod
    def populate_parser(cls, parser, ignore=frozenset()):
        schema_fields = vars(cls)['_declared_fields']

        for prop in schema_fields:

            if prop in ignore:
                continue

            props = dict()
            field_type = str(type(schema_fields[prop]).__name__)

            # determine field type
            if field_type == 'Integer':
                props['type'] = int
            elif field_type == 'String':
                props['type'] = str
            elif field_type == 'Float':
                props['type'] = float
            else:
                raise LookupError("Could not map {}".format(field_type))

            # required prop?
            props['required'] = schema_fields[prop].required

            try:
                props['help'] = schema_fields[prop].metadata['description']
            except KeyError:
                pass

            try:
                props['choices'] = list(schema_fields[prop].metadata['choices'])
            except KeyError:
                pass

            parser.add_argument(str(prop), **props)
