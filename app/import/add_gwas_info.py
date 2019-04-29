from queries.gwas_info_node import GwasInfo
from schemas.gwas_info_node_schema import GwasInfoNodeSchema
import flask
import logging
from resources._neo4j import Neo4j
from marshmallow import ValidationError

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')


def batch_add_nodes(nodes, label):
    logging.info("importing: {} n={}".format(label, len(nodes)))
    tx = Neo4j.get_db()
    tx.run("UNWIND $props AS map "
           "CREATE (n:" + label + ") "
                                  "SET n = map;", props=nodes)


# import to neo4
app = flask.Flask(__name__)
app.teardown_appcontext(Neo4j.close_db)

with app.app_context():
    schema = GwasInfoNodeSchema()
    Neo4j.clear_db()
    GwasInfo.set_constraint()
    nodes = []

    # import gwas info
    with open('data/study_e.tsv') as f:
        # skip first row which are NULL
        f.readline()

        for line in f:
            fields = line.strip().split("\t")
            d = dict()

            d['id'] = str(fields[0])
            try:
                d['pmid'] = int(fields[1])
            except ValueError as e:
                logging.warning(e)

            try:
                if int(fields[2]) > 0:
                    d['year'] = int(fields[2])
            except ValueError as e:
                logging.warning(e)

            if fields[3] != "NULL":
                d['filename'] = str(fields[3])

            if fields[4] != "NULL":
                d['path'] = str(fields[4])
            d['mr'] = int(fields[5])

            if fields[6] != "NULL":
                d['note'] = str(fields[6])

            if fields[7] != "NULL":
                d['trait'] = str(fields[7])

            # TODO should be None
            if fields[8] == "NULL" or fields[8] == "":
                d['category'] = "NA"
            else:
                d['category'] = str(fields[8])

            # TODO should be None
            if fields[9] == "NULL" or fields[9] == "":
                d['subcategory'] = "NA"
            else:
                d['subcategory'] = str(fields[9])

            if fields[10] == "NULL" or fields[10] == "" or fields[10] == "population":
                d['population'] = "NA"
            else:
                d['population'] = str(fields[10])

            if str(fields[11]) == "Males and females":
                d['sex'] = "Males and Females"
            elif fields[11] != "NULL":
                d['sex'] = str(fields[11])

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
                logging.warning(e)

            d['nsnp'] = int(fields[15])

            if fields[16] != "NULL":
                d['unit'] = str(fields[16])

            try:
                if fields[17] is not None:
                    d['sd'] = float(fields[17])
            except ValueError as e:
                logging.warning(e)

            try:
                d['priority'] = int(fields[18])
            except ValueError as e:
                d['priority'] = 0

            if fields[19] != "NULL":
                d['author'] = str(fields[19])

            if fields[20] != "NULL":
                d['consortium'] = str(fields[20])

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

            # validation
            try:
                d = schema.load(d)
            except ValidationError as e:
                logging.error("Could not import {} because {}".format(line, e))
                continue

            # append to import queue
            nodes.append(d)

            if len(nodes) > 5000:
                batch_add_nodes(nodes, GwasInfo.get_node_label())
                nodes = []

    # add remaining nodes
    batch_add_nodes(nodes, GwasInfo.get_node_label())
