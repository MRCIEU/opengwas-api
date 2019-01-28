from marshmallow import fields, ValidationError
from schemas.frpm_schema import FRPMSchema

valid_alleles = {'A', 'T', 'C', 'G', 'a', 't', 'c', 'g', 'I', 'i', 'd', 'd'}


def check_alleles(data):
    if data not in valid_alleles:
        raise ValidationError("Allele must be one of: {}".format(valid_alleles))


class GwasRowSchema(FRPMSchema):
    snp = fields.Str(required=False, allow_none=True, description="dbsnp identifier for variant")
    ea = fields.Str(required=True, allow_none=False, validate=check_alleles, description="Effect allele")
    oa = fields.Str(required=True, allow_none=False, validate=check_alleles, description="Other allele")
    eaf = fields.Float(required=False, allow_none=True, description="Effect allele frequency")
    beta = fields.Float(required=True, allow_none=False, description="Effect size")
    se = fields.Float(required=True, allow_none=False, description="Standard error of estimate")
    pval = fields.Float(required=True, allow_none=False, description="P-value")
    ncontrol = fields.Int(required=True, allow_none=False,
                          description="Number of controls or total sample size if continuous")
    ncase = fields.Int(required=False, allow_none=True,
                       description="Number of cases")
    chr = fields.String(required=False, allow_none=True, description="Variant chromosome")
    pos = fields.String(required=False, allow_none=True, description="Variant base position")
