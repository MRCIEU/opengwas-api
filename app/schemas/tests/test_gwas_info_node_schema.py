from schemas.gwas_info_node_schema import GwasInfoNodeSchema
from flask_restx import Resource, reqparse, Namespace, fields

d = {'id': '100', 'pmid': 23754948, 'year': 2013, 'mr': 1, 'note': 'Adjusted for BMI',
     'trait': 'Hip circumference', 'category': 'Risk factor', 'subcategory': 'Anthropometric', 'population': 'European',
     'sex': 'Males', 'ncase': None, 'ncontrol': None, 'sample_size': 60586, 'nsnp': 2725796, 'unit': 'SD (cm)',
     'sd': 8.4548, 'priority': 15, 'author': 'Randall JC', 'consortium': 'GIANT'}


def test_schema():
    schema = GwasInfoNodeSchema()
    schema.load(d)

    assert "consortium" in schema.load(d)
    assert "author" in schema.load(d)

    # check consortium is filled with NA which is not essential but required for downstream apps
    d2 = d
    del d2["consortium"]
    assert schema.load(d2)["consortium"] == "NA"

    # check author is filled with NA which is not essential but required for downstream apps
    d2 = d
    del d2["author"]
    assert schema.load(d2)["author"] == "NA"

    # check year is filled with NA which is not essential but required for downstream apps
    d2 = d
    del d2["year"]
    assert schema.load(d2)["year"] is None
    d2 = d
    d2["year"] = None
    assert schema.load(d2)["year"] is None


def test_populate_parser():
    api = Namespace('gwasinfo', description="Get information about available GWAS summary datasets")
    parser = api.parser()
    GwasInfoNodeSchema.populate_parser(parser)
