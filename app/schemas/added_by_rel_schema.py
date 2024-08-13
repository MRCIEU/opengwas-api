from marshmallow import fields, validate, ValidationError

from schemas.frpm_schema import FRPMSchema


def check_epoch_is_valid(data):
    if data < 1548343671 or data > 2526650871:
        raise ValidationError("Epoch is not valid")


class AddedByRelSchema(FRPMSchema):
    epoch = fields.Float(required=True, allow_none=False,
                       metadata={"description": "Unix timestamp: time recorded as number of milliseconds past 01.01.1970"})
    state = fields.Int(required=False, validate=validate.OneOf([0, 1, 2, 3, 4]), metadata={"description": "State of the dataset (released dataset will not have this field)"})
