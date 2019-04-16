from queries.gwas_info_node import GwasInfo
import flask
import logging
from marshmallow.exceptions import ValidationError
from resources._neo4j import Neo4j


def add_nodes(nodes, label):
    print("importing")
    tx = Neo4j.get_db()
    tx.run(
        "UNWIND {nodes} AS d "
        "MERGE (n:" + label + ") SET n = {d};",
        nodes=nodes
    )


app = flask.Flask(__name__)
app.teardown_appcontext(Neo4j.close_db)

with app.app_context():
    Neo4j.clear_db()
    GwasInfo.set_constraint()
    nodes = []

    # import gwas info
    with open('data/study_e.tsv') as f:
        # skip first row which are NULL
        f.readline()

        for line in f:
            fields = line.split("\t")
            d = dict()

            d['id'] = str(fields[0])
            try:
                d['pmid'] = int(fields[1])
            except ValueError as e:
                print(e)

            try:
                if int(fields[2]) > 0:
                    d['year'] = int(fields[2])
            except ValueError as e:
                print(e)

            d['filename'] = str(fields[3])
            d['path'] = str(fields[4])
            d['mr'] = int(fields[5])
            d['note'] = str(fields[6])
            d['trait'] = str(fields[7])
            d['category'] = str(fields[8])
            d['subcategory'] = str(fields[9])
            d['population'] = str(fields[10])

            try:
                if str(fields[11]) == "Males and females":
                    d['sex'] = "Males and Females"
                else:
                    d['sex'] = str(fields[11])
            except ValidationError as e:
                logging.error("Could not read field: {}".format(fields[11]))
                raise e

            try:
                d['ncase'] = int(fields[12])
            except ValueError as e:
                logging.warning(e)

            try:
                d['ncontrol'] = int(fields[13])
            except ValueError as e:
                logging.warning(e)

            try:
                d['sample_size'] = int(fields[14])
            except ValueError as e:
                print(e)

            d['nsnp'] = int(fields[15])
            d['unit'] = str(fields[16])
            try:
                d['sd'] = float(fields[17])
            except ValueError as e:
                print(e)
            try:
                d['priority'] = int(fields[18])
            except ValueError as e:
                d['priority'] = 0
            d['author'] = str(fields[19])
            d['consortium'] = str(fields[20])

            if d['category'] == "NULL":
                d['category'] = "NA"

            if d['subcategory'] == "NULL":
                d['subcategory'] = "NA"

            if d['category'] == "Cytokines":
                d['category'] = "Immune system"

            if d['subcategory'] == "Lung":
                d['subcategory'] = "NA"

            if d['subcategory'] == "Gene expression":
                d['subcategory'] = "NA"

            if d['sex'] == "Male and female":
                d['sex'] = "Males and Females"

            if d['category'] == "Molecular":
                d['category'] = "NA"

            nodes.append(d)

            if len(nodes) > 5000:
                add_nodes(nodes, GwasInfo.get_uid_key())
                nodes = []

    # add remaining nodes
    add_nodes(nodes, GwasInfo.get_uid_key())
