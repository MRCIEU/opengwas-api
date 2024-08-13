import datetime

from marshmallow import fields, validate, ValidationError
from schemas.frpm_schema import FRPMSchema
from schemas.group_node_schema import valid_group_names
import re

pattern = re.compile(r'\b(10[.])')

valid_genome_build = ['HG19/GRCh37']

valid_categories = [
    'Immune system',
    'NA',
    'Risk factor',
    'Continuous',
    'Metabolites',
    'Binary',
    'Disease',
    'Categorical Ordered'
]

valid_subcategories = [
    "Anthropometric",
    "Psychiatric / neurological",
    "Education",
    "Hormone",
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
    "NA"
]

valid_populations = [
    "Aboriginal Australian", "African American or Afro-Caribbean", "African unspecified", "Asian unspecified",
    "Central Asian", "East Asian", "European", "Greater Middle Eastern (Middle Eastern, North African, or Persian)",
    "Hispanic or Latin American", "Native American", "Not reported", "Oceanian", "Other", "Other admixed ancestry",
    "South Asian", "South East Asian", "Sub-Saharan African", "Mixed", "NA"
]

valid_sex = ['Males and Females', 'Males', 'Females', 'NA']

valid_study_designs = [
    "Meta-analysis of case-control studies",
    "Meta-analysis of cohort/cross-sectional studies",
    "Meta-analysis of studies with varying designs",
    "Case-control study",
    "Cohort/cross-sectional study",
    "Case-only analysis",
    "Other",
    "Unknown"
]

valid_imputation_panels = ['not imputed', 'HapMap2', 'HapMap3', '1000 Genomes', 'UK10K', 'HRC', 'TOPMed', 'other']

valid_coverage = ["whole genome", "partial", "exome"]


def check_study_year(data):
    if data < 2000 or data > 2050:
        raise ValidationError("Study year is invalid")


def check_mr_is_0_or_1(data):
    if data < 0 or data > 1:
        raise ValidationError("MR must be 0 or 1")


def check_trait_description(data):
    if data not in valid_trait_descriptions:
        raise ValidationError("Trait description must be one of: {}".format(valid_trait_descriptions))


def check_category_is_valid(data):
    if data not in valid_categories:
        raise ValidationError("Trait category must be one of: {}".format(valid_categories))


def check_subcategory_is_valid(data):
    if data not in valid_subcategories:
        raise ValidationError("Trait subcategory must be one of: {}".format(valid_subcategories))


def check_population_is_valid(data):
    if data not in valid_populations:
        raise ValidationError("Population must be one of: {}".format(valid_populations))


def check_group_name_is_valid(data):
    if data not in valid_group_names:
        raise ValidationError("Group name must be one of: {}".format(valid_group_names))


def check_sex_is_valid(data):
    if data not in valid_sex:
        raise ValidationError("Sex must be one of: {}".format(valid_sex))


def check_study_design_is_valid(data):
    if data not in valid_study_designs:
        raise ValidationError("Study design must be one of: {}".format(valid_study_designs))


def check_imputation_panel_is_valid(data):
    if data not in valid_imputation_panels:
        raise ValidationError("Imputation panel must be one of: {}".format(valid_imputation_panels))


def check_genome_build_is_valid(data):
    if data not in valid_genome_build:
        raise ValidationError("Imputation panel must be one of: {}".format(valid_genome_build))


def check_doi(data):
    if not pattern.match(data):
        raise ValidationError("DOI is invalid: {}".format(data))


def check_id_is_valid_filename(data):
    if data is not None and not re.match(r'^[\w-]+$', data) is not None:
        raise ValidationError(
            "Identifier can only contain alphanumeric, dash and underscore. {} is invalid".format(data)
        )


class GwasInfoNodeSchema(FRPMSchema):
    id = fields.Str(required=True, validate=check_id_is_valid_filename, metadata={"description": "Dataset ID on OpenGWAS"})
    trait = fields.Str(required=True, metadata={"description": "Avoid acronyms; don't include other information in the trait name (e.g. don't include array name, whether restricted to males or females or whether adjusted or unadjusted for covariates)"})
    build = fields.Str(required=True, validate=validate.OneOf(valid_genome_build), metadata={"description": "Select the genome build for the dataset. Must be HG19/GRCh37. If not, please convert the files before uploading it for QC", "choices": sorted(valid_genome_build)})
    group_name = fields.Str(required=True, validate=validate.OneOf(valid_group_names), metadata={"description": "Who can access this dataset once uploaded? Contact us if you need to create/reuse a specific group to restrict access", "choices": sorted(valid_group_names)})
    category = fields.Str(required=True, validate=validate.OneOf(valid_categories), metadata={"description": "Is your phenotype a binary disease phenotype or a non-disease phenotype?", "choices": sorted(valid_categories)})
    subcategory = fields.Str(required=True, validate=validate.OneOf(valid_subcategories), metadata={"description": "Select the option that best describes your phenotype", "choices": sorted(valid_subcategories)})
    population = fields.Str(required=True, validate=validate.OneOf(valid_populations), metadata={"description": "Describe the geographic origins of your population", "choices": sorted(valid_populations)})
    sex = fields.Str(required=True, validate=validate.OneOf(valid_sex), metadata={"description": "Indicate whether males or females are included in the study", "choices": sorted(valid_sex)})
    ontology = fields.Str(required=True, metadata={"description": "Ontology mapping, semi-colon separated (e.g. MONDO:0003274;EFO:0000311)"})
    unit = fields.Str(required=True, metadata={"description": "How do you interpret a 1-unit change in the phenotype? (e.g. log odds ratio, mmol/L, SD)"})
    sample_size = fields.Int(required=True, metadata={"description": "Provide the sample size of your study"})
    author = fields.Str(required=True, metadata={"description": "Provide the last name and initials of the first author of your study (e.g. Mendel GJ)"})
    year = fields.Int(required=True, validate=validate.Range(2000, datetime.datetime.now().year + 1), metadata={"description": "In which year was this GWAS published?"})

    nsnp = fields.Int(allow_none=True, metadata={"description": "How many SNPs are in your results file that you are uploading?"})

    ncase = fields.Int(allow_none=True, metadata={"description": "Provide number of cases in the dataset (if applicable)"})
    ncontrol = fields.Int(allow_none=True, metadata={"description": "Provide number of controls in the dataset (if applicable)"})
    study_design = fields.Str(allow_none=True, validate=validate.OneOf(valid_study_designs), metadata={"description": "Which best describes the design of the study?", "choices": sorted(valid_study_designs)})
    covariates = fields.Str(allow_none=True, metadata={"description": "Describe the covariates included in your regression model"})
    coverage = fields.Str(allow_none=True, validate=validate.OneOf(valid_coverage), metadata={"description": "Level of genome coverage", "choices": valid_coverage})
    qc_prior_to_upload = fields.Str(allow_none=True, metadata={"description": "Detail any QC or filtering steps taken prior to data upload"})
    imputation_panel = fields.Str(allow_none=True, validate=validate.OneOf(valid_imputation_panels), metadata={"description": "Select the imputation panel used in the study", "choices": sorted(valid_imputation_panels)})
    beta_transformation = fields.Str(allow_none=True, metadata={"description": "Describe transformations applied to your phenotype (e.g. inverse rank normal, Z transformations)"})
    doi = fields.Str(allow_none=True, validate=validate.Regexp(pattern), metadata={"description": "DOI. Leave blank for unpublished studies (e.g. 10.1101/2020.08.10.244293v1)"},)
    consortium = fields.Str(allow_none=True, metadata={"description": "What is the name of the consortium (if applicable)? E.g. UK Biobank"})
    pmid = fields.Int(allow_none=True, metadata={"description": "PubMed identifier (digits only). Leave blank for unpublished studies"})
    sd = fields.Float(allow_none=True, metadata={"description": "What is the standard deviation of the sample mean of the phenotype?"})
    mr = fields.Int(allow_none=True, validate=validate.OneOf([0, 1]), metadata={"description": "Is the dataset suitable for MR studies? Put 1 for yes, or 0 for no (digits only)", "choices": [0, 1]})
    priority = fields.Int(allow_none=True, metadata={"description": "If multiple datasets with the same trait name exist, where does this dataset rank in terms of priority"})
    note = fields.Str(allow_none=True, metadata={"description": "Is there any other information you would like to provide us about your GWAS?"})
