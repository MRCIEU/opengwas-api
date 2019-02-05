from marshmallow import fields, ValidationError
from schemas.frpm_schema import FRPMSchema


def check_epoch_is_valid(data):
    if data < 1548343671 or data > 2526650871:
        raise ValidationError("Epoch is not valid")


class QualityControlRelSchema(FRPMSchema):
    data_passed = fields.Bool(required=True, allow_none=False, description="Did the data meet QC?")
    comment = fields.String(required=False, allow_none=True, description="Comment on the QC")
    epoch = fields.Float(required=True, allow_none=False, description="Time", validate=check_epoch_is_valid)
