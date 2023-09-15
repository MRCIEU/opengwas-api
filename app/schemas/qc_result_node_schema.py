from marshmallow import fields
from marshmallow.exceptions import ValidationError
from schemas.frpm_schema import FRPMSchema
import re


def check_id_is_valid_filename(data):
    if data is not None and not re.match(r'^[\w-]+$', data) is not None:
        raise ValidationError( "Identifier can only contain alphanumeric, hash and underscore. {} is invalid".format(data))


class QCResultNodeSchema(FRPMSchema):
    id = fields.Str(required=True, allow_none=False, description="GWAS study identifier", validate=check_id_is_valid_filename)
    n_snps = fields.Int(required=False, allow_none=True, description="Number of SNPs")