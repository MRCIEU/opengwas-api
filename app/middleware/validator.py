from schemas import *


class Validator:
    def __init__(self, schema_name, partial=False):
        self.schema = globals()[schema_name](partial=partial)

    def validate(self, data):
        errors = self.schema.validate(data)
        message = " ".join([field + " " + error[0] for field, error in errors.items()])
        if message:
            raise Exception(message)
