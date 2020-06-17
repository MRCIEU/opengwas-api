from marshmallow import fields, ValidationError
from schemas.frpm_schema import FRPMSchema
from schemas.group_node_schema import valid_group_names
import idutils
import re

valid_trait_subcategories = {
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
    "subcategory",
    "NA"
}

valid_trait_descriptions = {'Continuous', 'Binary', 'Ordinal', 'Categorical Ordered'}
valid_categories = {'Immune system', 'NA', 'Risk factor', 'Continuous', 'Metabolites', 'Disease', 'Binary',
                    'Categorical Ordered'}
valid_populations = {
    "Aboriginal Australian", "African American or Afro-Caribbean", "African unspecified", "Asian unspecified",
    "Central Asian", "East Asian", "European", "Greater Middle Eastern (Middle Eastern, North African, or Persian)",
    "Hispanic or Latin American", "Native American", "Not reported", "Oceanian", "Other", "Other admixed ancestry",
    "South Asian", "South East Asian", "Sub-Saharan African", "Mixed", "NA"
}
valid_sex = {'Males and Females', 'Males', 'Females', 'NA'}
valid_study_designs = {
    "Meta-analysis of case-control studies",
    "Meta-analysis of cohort/cross-sectional studies",
    "Meta-analysis of studies with varying designs",
    "Case-control study",
    "Cohort/cross-sectional study",
    "Case-only analysis",
    "Other",
    "Unknown"
}
valid_imputation_panels = {'not imputed', 'HapMap2', 'HapMap3', '1000 Genomes', 'UK10K', 'HRC', 'TOPMed', 'other'}
valid_genome_build = {'HG19/GRCh37'}

valid_coverage = {
    "whole genome", "partial", "exome"
}

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
    if data not in valid_trait_subcategories:
        raise ValidationError("Trait subcategory must be one of: {}".format(valid_trait_subcategories))


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
    if not idutils.is_doi:
        raise ValidationError("DOI is invalid: {}".format(data))


def check_id_is_valid_filename(data):
    if data is not None and not re.match(r'^[\w-]+$', data) is not None:
        raise ValidationError(
            "Identifier can only contain alphanumeric, hash and underscore. {} is invalid".format(data)
        )


class GwasInfoNodeSchema(FRPMSchema):
    id = fields.Str(required=True, allow_none=False,
        description="GWAS study identifier",
        validate=check_id_is_valid_filename)
    pmid = fields.Int(required=False, allow_none=True,
        description="Pubmed identifier. Leave blank for unpublished studies.")
    doi = fields.Str(required=False, allow_none=True,
        description="DOI. Leave blank for unpublished studies.",
        validate=check_doi)
    year = fields.Int(required=False, validate=check_study_year, allow_none=True,
        description="What year was this GWAS published?")
    mr = fields.Int(required=False, allow_none=True,
        validate=check_mr_is_0_or_1,
        description="Is the study suitable for MR studies?", choices=(0, 1))
    note = fields.Str(required=False, allow_none=True,
        description="Is there any other information you would like to provide us about your GWAS?")
    trait = fields.Str(required=True, allow_none=False,
        description="Avoid acronyms; don't include other information in the trait name (e.g. don't include array name, whether restricted to males or females or whether adjusted or unadjusted for covariates)")
    #trait_description = fields.Str(required=False, validate=check_trait_description, allow_none=True,
        # choices=sorted(list(valid_trait_descriptions)),
        # description="Describe the distribution of your phenotype")
    category = fields.Str(required=True, validate=check_category_is_valid, allow_none=False,
        description="Is your phenotype a binary disease phenotype or a non-disease phenotype",
        choices=sorted(list(valid_categories)))
    subcategory = fields.Str(required=True, allow_none=False,
        validate=check_subcategory_is_valid,
        description="Select the option that best describes your phenotype.",
        choices=sorted(list(valid_trait_subcategories)))
    ontology = fields.Str(required=False, allow_none=True,
        description="Ontology mapping, semi-colon separated, e.g. 'MONDO:0003274;EFO:0000311'")
    population = fields.Str(required=True, validate=check_population_is_valid, allow_none=False,
        description="Describe the geographic origins of your population",
        choices=sorted(list(valid_populations)))
    sex = fields.Str(required=True, validate=check_sex_is_valid, allow_none=False,
        description="Indicate whether males or females are included in your study",
        choices=sorted(list(valid_sex)))
    ncase = fields.Int(required=False, allow_none=True,
        description="Provide number of cases in your study (if applicable)")
    ncontrol = fields.Int(required=False, allow_none=True,
        description="Provide number of controls in your study (if applicable)")
    sample_size = fields.Int(required=False, allow_none=True, description="Provide the sample size of your study")
    nsnp = fields.Int(required=False, allow_none=True,
        description="How many SNPs are in your results file that you are uploading?")
    unit = fields.Str(required=False, allow_none=True,
        description="How do you interpret a 1-unit change in the phenotype? eg log odds ratio, mmol/L, SD units?")
    sd = fields.Float(required=False, allow_none=True,
        description="What is the standard deviation of the sample mean of the phenotype?")
    priority = fields.Int(required=True, allow_none=False)
    author = fields.Str(required=False, allow_none=True,missing="NA",
        description="Provide the last name of the first author of your study")
    consortium = fields.Str(required=False, allow_none=True, missing="NA",
        description="What is the name of your study or consortium (if applicable)?")
    study_design = fields.Str(required=False, validate=check_study_design_is_valid, allow_none=True,
        description="Which best describes the design of your study",
        choices=sorted(list(valid_study_designs)))
    covariates = fields.Str(required=False, allow_none=True,
        description="Describe the covariates included in your regression model")
    beta_transformation = fields.Str(required=False, allow_none=True,
        description="Describe transformations applied to your phenotype (e.g. inverse rank normal, Z transformations, etc)")
    imputation_panel = fields.Str(required=False, validate=check_imputation_panel_is_valid, allow_none=True,
        description="Select the imputation panel used in your study",
        choices=sorted(list(valid_imputation_panels)))
    build = fields.Str(required=False, validate=check_genome_build_is_valid, allow_none=True,
        description="Select the genome build for your study", choices=sorted(list(valid_genome_build)))
    coverage = fields.Str(required=False, allow_none=True,
        description="Level of genome coverage",
        choices=list(valid_coverage))
    qc_prior_to_upload = fields.Str(required=False, allow_none=True,
                                    description="Detail any QC or filtering steps taken prior to data upload")
    group_name = fields.Str(required=False, allow_none=True,
                    validate=check_group_name_is_valid,
                    description="Name for the group this study should belong to.", 
                    choices=sorted(list(valid_group_names)))
