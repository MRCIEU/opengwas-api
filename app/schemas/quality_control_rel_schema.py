from marshmallow import fields, ValidationError
from schemas.frpm_schema import FRPMSchema


class QualityControlRelSchema(FRPMSchema):
    data_passed = fields.Bool(required=True, allow_none=False, description="Did the data meet QC?")
    comment = fields.String(required=False, allow_none=True, description="Comment on the QC")
    epoch = fields.Int(required=True, allow_none=False, description="Time")
