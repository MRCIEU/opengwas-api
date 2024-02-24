from marshmallow import fields, ValidationError
from schemas.frpm_schema import FRPMSchema
import re

valid_alleles = {'a', 't', 'c', 'g', 'i', 'd'}
dbsnp_reg = re.compile('^rs[0-9]*')


def check_alleles(data):
    for c in data:
        if c.lower() not in valid_alleles:
            raise ValidationError("Allele must be one of: {}".format(valid_alleles))


def check_dbsnpid(data):
    if not dbsnp_reg.match(data):
        raise ValidationError("Invalid dbsnp identifier: {}".format(data))


class GwasRowSchema(FRPMSchema):
    snp = fields.Str(required=False, allow_none=True, validate=check_dbsnpid,
                     metadata={"description": "dbsnp identifier for variant"})
    ea = fields.Str(required=True, allow_none=False, validate=check_alleles, metadata={"description": "Effect allele"})
    oa = fields.Str(required=True, allow_none=False, validate=check_alleles, metadata={"description": "Other allele"})
    eaf = fields.Float(required=False, allow_none=True, metadata={"description": "Effect allele frequency"})
    beta = fields.Float(required=True, allow_none=False, metadata={"description": "Effect size"})
    se = fields.Float(required=True, allow_none=False, metadata={"description": "Standard error of estimate"})
    pval = fields.Float(required=True, allow_none=False, metadata={"description": "P-value"})
    ncontrol = fields.Float(required=False, allow_none=True,
                            metadata={"description": "Number of controls or total sample size if continuous"})
    ncase = fields.Int(required=False, allow_none=True,
                       metadata={"description": "Number of cases"})
    chr = fields.String(required=True, allow_none=False, metadata={"description": "Variant chromosome"})
    pos = fields.String(required=True, allow_none=False, metadata={"description": "Variant base position"})
