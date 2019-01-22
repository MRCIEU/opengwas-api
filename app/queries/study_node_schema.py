from marshmallow import Schema, fields, post_load, ValidationError
from queries.study_node import Study


class StudyNodeSchema(Schema):

    # TODO clean data
    @staticmethod
    def check_study_year(data):
        if data < 2000 or data > 2050:
            raise ValidationError("Study year is invalid")

    @staticmethod
    def check_mr_is_0_or_1(data):
        if data < 0 or data > 1:
            raise ValidationError("MR must be 0 or 1")

    @staticmethod
    def check_trait_description(data):
        valid = {'Continuous', 'Binary', 'Ordinal'}
        if data not in valid:
            raise ValidationError("Trait description must be one of: {}".format(valid))

    @staticmethod
    def check_category_is_valid(data):
        valid = {'Immune system', 'NA', 'Risk factor', 'Continuous', 'Metabolites', 'Disease', 'Binary',
                 'Catagorial Ordered'}
        if data not in valid:
            raise ValidationError("Trait category must be one of: {}".format(valid))

    # TODO remove ''
    @staticmethod
    def check_subcategory_is_valid(data):
        valid = {'NA', 'Metabolite salt', '', 'Sleeping', 'Immune cell-surface protein expression levels', 'Cancer',
                 'Unknown metabolite', 'Reproductive aging', 'Aging', 'Energy', 'Protein', 'Psychiatric / neurological',
                 'Peptide', 'Anthropometric', 'Nucleotide', 'Haemotological', 'Other', 'Xenobiotics',
                 'Paediatric disease', 'Kidney', 'Bone', 'Education', 'Fatty acid', 'Cardiovascular', 'Lipid', 'Eye',
                 'Cofactors and vitamins', 'Glycemic', 'Immune system', 'Keto acid', 'Metabolites ratio', 'Hemodynamic',
                 'Carbohydrate', 'Diabetes', 'Immune cell subset frequency', 'Hormone', 'Behavioural', 'Personality',
                 'Blood pressure', 'Autoimmune / inflammatory', 'Amino acid', 'Metal', 'Lung disease'}
        if data not in valid:
            raise ValidationError("Trait subcategory must be one of: {}".format(valid))

    @staticmethod
    def check_population_is_valid(data):
        valid = {'Chinese', 'European', 'African American', 'East Asian', 'Iranian', 'Indian', 'Hispanic', 'Mixed',
                 'Japanese'}
        if data not in valid:
            raise ValidationError("Population must be one of: {}".format(valid))

    # TODO clean data
    @staticmethod
    def check_sex_is_valid(data):
        valid = {'Males and Females', 'Males and females', 'Males', 'Females'}
        if data not in valid:
            raise ValidationError("Sex must be one of: {}".format(valid))

    # TODO clean data
    @staticmethod
    def check_access_is_valid(data):
        valid = {'public', 'Public'}
        if data not in valid:
            raise ValidationError("Access must be one of: {}".format(valid))

    @staticmethod
    def check_study_design_is_valid(data):
        valid = {'Meta-analysis of case-control studies', 'case-control study', 'cohort study',
                 'case-only survival analysis'}
        if data not in valid:
            raise ValidationError("Study design must be one of: {}".format(valid))

    @staticmethod
    def check_imputation_panel_is_valid(data):
        valid = {'no imputed genotypes', '1000 Genomes', 'HapMap', 'HRC', 'UK10K', 'other'}
        if data not in valid:
            raise ValidationError("Imputation panel must be one of: {}".format(valid))

    @staticmethod
    def check_genome_build_is_valid(data):
        valid = {'HG18/GRCh36', 'HG19/GRCh37', 'HG38/GRCh38'}
        if data not in valid:
            raise ValidationError("Imputation panel must be one of: {}".format(valid))

    id = fields.Str(required=True)
    pmid = fields.Int(required=True)
    year = fields.Int(required=True, validate=check_study_year)
    filename = fields.Str(required=True)
    path = fields.Str(required=True)
    mr = fields.Int(required=True, validate=check_mr_is_0_or_1)
    note = fields.Str(required=False)
    trait = fields.Str(required=True)
    trait_description = fields.Str(required=False, validate=check_trait_description)
    category = fields.Str(required=True, validate=check_category_is_valid)
    subcategory = fields.Str(required=True, validate=check_subcategory_is_valid)
    population = fields.Str(required=True, validate=check_population_is_valid)
    sex = fields.Str(required=True, validate=check_sex_is_valid)
    ncase = fields.Int(required=False)
    ncontrol = fields.Int(required=False)
    sample_size = fields.Int(required=True)
    nsnp = fields.Int(required=False)
    unit = fields.Str(required=True)
    sd = fields.Float(required=False)
    priority = fields.Int(required=True)
    author = fields.Str(required=True)
    consortium = fields.Str(required=False)
    access = fields.Str(required=False, validate=check_access_is_valid)
    study_design = fields.Str(required=False, validate=check_study_design_is_valid)
    covariates = fields.Str(required=False)
    beta_transformation = fields.Str(required=False)
    imputation_panel = fields.Str(required=False, validate=check_imputation_panel_is_valid)
    build = fields.Str(required=False, validate=check_genome_build_is_valid)

    @post_load
    def make(self, data):
        return Study(**data)
