from schemas.frpm_schema import FRPMSchema
from marshmallow import fields, ValidationError


def check_epoch_is_valid(data):
    if data < 1548343671 or data > 2526650871:
        raise ValidationError("Epoch is not valid")


class AddedByRelSchema(FRPMSchema):
    epoch = fields.Float(required=True, allow_none=False,
                       metadata={"description": "Unix timestamp: time recorded as number of miliseconds past 01.01.1970"})
