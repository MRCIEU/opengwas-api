from marshmallow import fields
from marshmallow.exceptions import ValidationError
from schemas.frpm_schema import FRPMSchema

valid_group_names = {
    "public",
    "developer",
    "Bristol",
    "charge_igf",
    "immunobase_users",
    "SpiroMetaplusCHARGE",
    "Onco_TRICL_lung_cancer",
    "Ahola-Olli_Cytokines",
    "BCAC",
    "Thompson_JIA",
    "EmmaLA",
    "practical",
    "biogen",
    "Huntingtons",
    "King_GSK",
    "OCAC",
    "GSK",
    "GTEx",
    "pQTL",
    "eQTLGen",
    "sclerostin",
    "biobank_japan",
    "small_ukb-b",
    "ncase_lt_10_ukb-b",
    "CHDI",
    "internal",
    "Sclerostin_genetics_consortium",
    "headspace"
}


def check_group_name_is_valid(data):
    if data not in valid_group_names:
        raise ValidationError("Group name must be one of: {}".format(valid_group_names))


class GroupNodeSchema(FRPMSchema):
    name = fields.Str(required=True, allow_none=False, metadata={"description": "Group name"}, validate=check_group_name_is_valid)
