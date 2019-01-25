from schemas.gwas_info_node_schema import GwasInfoNodeSchema
from flask_restplus import Resource, reqparse, Namespace, fields

d = {'id': '100', 'pmid': 23754948, 'year': 2013,
     'filename': 'GIANT_Randall2013PlosGenet_stage1_publicrelease_HapMapCeuFreq_HIPadjBMI_MEN_N.txt.tab',
     'path': '/projects/MRC-IEU/publicdata/GWAS_summary_data/GIANT_2010_2012_2013', 'mr': 1, 'note': 'Adjusted for BMI',
     'trait': 'Hip circumference', 'category': 'Risk factor', 'subcategory': 'Anthropometric', 'population': 'European',
     'sex': 'Males', 'ncase': None, 'ncontrol': None, 'sample_size': 60586, 'nsnp': 2725796, 'unit': 'SD (cm)',
     'sd': 8.4548, 'priority': 15, 'author': 'Randall JC', 'consortium': 'GIANT', 'access': 'public'}


def test_schema():
    schema = GwasInfoNodeSchema()
    schema.load(d)


def test_populate_parser():
    api = Namespace('gwasinfo', description="Get information about available GWAS summary datasets")
    parser = api.parser()
    GwasInfoNodeSchema.populate_parser(parser)