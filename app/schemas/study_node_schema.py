from marshmallow import fields, ValidationError, post_load
from queries.study_node import Study
from schemas.frpm_schema import FRPMSchema


def check_study_year(data):
    if data < 2000 or data > 2050:
        raise ValidationError("Study year is invalid")


def check_mr_is_0_or_1(data):
    if data < 0 or data > 1:
        raise ValidationError("MR must be 0 or 1")


def check_trait_description(data):
    valid = {'Continuous', 'Binary', 'Ordinal'}
    if data not in valid:
        raise ValidationError("Trait description must be one of: {}".format(valid))


def check_category_is_valid(data):
    valid = {'Immune system', 'NA', 'Risk factor', 'Continuous', 'Metabolites', 'Disease', 'Binary',
             'Catagorial Ordered'}
    if data not in valid:
        raise ValidationError("Trait category must be one of: {}".format(valid))


def check_subcategory_is_valid(data):
    valid = {"Anthropometric", "Psychiatric / neurological", "Education", "Hormone",
             "Reproductive aging",
             "Lung disease",
             "Haemotological",
             "Personality",
             "Cancer",
             "Immune system",
             "Autoimmune / inflammatory",
             "Cardiovascular",
             "Lipid",
             "Metal",
             "Other",
             "Hemodynamic",
             "Kidney",
             "Sleeping",
             "Diabetes",
             "Aging",
             "null",
             "Fatty acid",
             "Bone",
             "Immune cell subset frequency",
             "Cytokines",
             "Immune cell-surface protein expression levels",
             "Eye",
             "Amino acid",
             "Carbohydrate",
             "Nucleotide",
             "Energy",
             "Cofactors and vitamins",
             "Peptide",
             "Unknown metabolite",
             "Xenobiotics",
             "Glycemic",
             "Protein",
             "Behavioural",
             "Blood pressure",
             "Keto acid",
             "Metabolite salt",
             "Metabolites ratio",
             "Lung function",
             "Paediatric disease",
             "Growth hormone",
             "Biomarker",
             "gtex_eqtl",
             "subcategory",
             "NA"}

    if data not in valid:
        raise ValidationError("Trait subcategory must be one of: {}".format(valid))


def check_population_is_valid(data):
    valid = {'Chinese', 'European', 'African American', 'East Asian', 'Iranian', 'Indian', 'Hispanic', 'Mixed',
             'Japanese'}
    if data not in valid:
        raise ValidationError("Population must be one of: {}".format(valid))


def check_sex_is_valid(data):
    valid = {'Males and Females', 'Males', 'Females'}
    if data not in valid:
        raise ValidationError("Sex must be one of: {}".format(valid))


def check_access_is_valid(data):
    valid = {'public', 'Public'}
    if data not in valid:
        raise ValidationError("Access must be one of: {}".format(valid))


def check_study_design_is_valid(data):
    valid = {'Meta-analysis of case-control studies', 'case-control study', 'cohort study',
             'case-only survival analysis'}
    if data not in valid:
        raise ValidationError("Study design must be one of: {}".format(valid))


def check_imputation_panel_is_valid(data):
    valid = {'no imputed genotypes', '1000 Genomes', 'HapMap', 'HRC', 'UK10K', 'other'}
    if data not in valid:
        raise ValidationError("Imputation panel must be one of: {}".format(valid))


def check_genome_build_is_valid(data):
    valid = {'HG18/GRCh36', 'HG19/GRCh37', 'HG38/GRCh38'}
    if data not in valid:
        raise ValidationError("Imputation panel must be one of: {}".format(valid))


class StudyNodeSchema(FRPMSchema):
    id = fields.Str(required=True, allow_none=False)
    pmid = fields.Int(required=False, allow_none=True)
    year = fields.Int(required=False, validate=check_study_year, allow_none=True)
    filename = fields.Str(required=False, allow_none=False)
    path = fields.Str(required=True, allow_none=False)
    mr = fields.Int(required=True, validate=check_mr_is_0_or_1, allow_none=False)
    note = fields.Str(required=False, allow_none=True)
    trait = fields.Str(required=True, allow_none=False)
    trait_description = fields.Str(required=False, validate=check_trait_description, allow_none=True)
    category = fields.Str(required=True, validate=check_category_is_valid, allow_none=False)
    subcategory = fields.Str(required=True, validate=check_subcategory_is_valid, allow_none=False)
    population = fields.Str(required=True, validate=check_population_is_valid, allow_none=False)
    sex = fields.Str(required=True, validate=check_sex_is_valid, allow_none=False)
    ncase = fields.Int(required=False, allow_none=True)
    ncontrol = fields.Int(required=False, allow_none=True)
    sample_size = fields.Int(required=False, allow_none=True)
    nsnp = fields.Int(required=False, allow_none=True)
    unit = fields.Str(required=True, allow_none=False)
    sd = fields.Float(required=False, allow_none=True)
    priority = fields.Int(required=True, allow_none=False)
    author = fields.Str(required=True, allow_none=False)
    consortium = fields.Str(required=False, allow_none=True)
    access = fields.Str(required=False, allow_none=True)
    study_design = fields.Str(required=False, validate=check_study_design_is_valid, allow_none=True)
    covariates = fields.Str(required=False, allow_none=True)
    beta_transformation = fields.Str(required=False, allow_none=True)
    imputation_panel = fields.Str(required=False, validate=check_imputation_panel_is_valid, allow_none=True)
    build = fields.Str(required=False, validate=check_genome_build_is_valid, allow_none=True)
    status = fields.Str(required=False, allow_none=True)

    @post_load
    def map_to_obj(self, data):
        return Study(**data)
