from queries.study_node_queries import *
import flask
import pytest

record = {'id': 'test100', 'pmid': 23754948, 'year': 2013,
          'filename': 'GIANT_Randall2013PlosGenet_stage1_publicrelease_HapMapCeuFreq_HIPadjBMI_MEN_N.txt.tab',
          'path': '/projects/MRC-IEU/publicdata/GWAS_summary_data/GIANT_2010_2012_2013', 'mr': 1,
          'note': 'Adjusted for BMI', 'trait': 'Hip circumference', 'category': 'Risk factor',
          'subcategory': 'Anthropometric', 'population': 'European', 'sex': 'Males', 'ncase': None, 'ncontrol': None,
          'sample_size': 60586, 'nsnp': 2725796, 'unit': 'SD (cm)', 'sd': 8.4548, 'priority': 15,
          'author': 'Randall JC', 'consortium': 'GIANT', 'access': 'public'}

app = flask.Flask(__name__)


def test_add_study():
    with app.app_context():
        add_study(record)
        res = get_study(record['id'])

        for k in record:
            assert res[k] == record[k]


def test_delete_study():
    with app.app_context():
        delete_study(record['id'])

        with pytest.raises(LookupError):
            get_study(record['id'])
