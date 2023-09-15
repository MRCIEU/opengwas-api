from marshmallow import fields, ValidationError
from schemas.frpm_schema import FRPMSchema


def check_epoch_is_valid(data):
    if data < 1548343671 or data > 2526650871:
        raise ValidationError("Epoch is not valid")


class QCResultRelSchema(FRPMSchema):
    epoch = fields.Float(required=True, allow_none=False, description="Time", validate=check_epoch_is_valid)
