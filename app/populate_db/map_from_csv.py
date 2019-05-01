from queries.group_node import Group
from queries.user_node import User
from queries.access_to_rel import AccessToRel
from queries.cql_queries import add_new_user
from queries.gwas_info_node import GwasInfo
from schemas.gwas_info_node_schema import GwasInfoNodeSchema
import flask
import logging
from resources.neo4j import Neo4j
from marshmallow import ValidationError

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')


def batch_add_nodes(nodes, label):
    logging.info("importing: {} n={}".format(label, len(nodes)))
    tx = Neo4j.get_db()
    tx.run("UNWIND $props AS map "
           "CREATE (n:" + label + ") "
                                  "SET n = map;", props=nodes)


def batch_add_rel(records):
    logging.info("importing: n={}".format(len(records)))
    tx = Neo4j.get_db()
    tx.run("UNWIND $props AS map "
           "MATCH (gi:GwasInfo) where gi.id = map.gwas_id "
           "MATCH (grp:Group) where grp.name = map.grp_id "
           "MERGE (grp)-[:ACCESS_TO]->(gi);", props=records)


def map_population(pop):
    if pop.lower() == "african american":
        return "African American or Afro-Caribbean"
    elif pop.lower() == "chinese, japanese, east asian":
        return "East Asian"
    elif pop.lower() == "japan":
        return "East Asian"
    elif pop.lower() == "japanese":
        return "East Asian"
    elif pop.lower() == "chinese":
        return "East Asian"
    elif pop.lower() == "european":
        return "European"
    elif pop.lower() == "iranian":
        return "Greater Middle Eastern (Middle Eastern, North African, or Persian)"
    elif pop.lower() == "hispanic":
        return "Hispanic or Latin American"
    elif pop.lower() == "indian":
        return "South Asian"
    elif pop.lower() == "mixed":
        return "Mixed"
    elif pop.lower() == "na":
        return "NA"
    else:
        raise ValueError("Unknown pop :{}".format(pop))


# populate_db to neo4
app = flask.Flask(__name__)
app.teardown_appcontext(Neo4j.close_db)

with app.app_context():
    schema = GwasInfoNodeSchema()
    Neo4j.clear_db()
    Group.set_constraint()
    User.set_constraint()
    GwasInfo.set_constraint()
    access_to_rel = AccessToRel()
    nodes = []
    gid_to_name = dict()
    email_to_gid = dict()
    all_gwas_id = set()

    # populate_db gwas info
    with open('populate_db/data/study_e.tsv') as f:
        # skip first row which are NULL
        f.readline()

        for line in f:
            fields = line.strip().split("\t")
            d = dict()

            d['id'] = str(fields[0])
            all_gwas_id.add(str(fields[0]))

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

            # TODO should be None
            if fields[10] == "NULL" or fields[10] == "" or fields[10] == "population":
                d['population'] = "NA"
            else:
                d['population'] = str(fields[10])

            d['population'] = map_population(d['population'])

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
                logging.error("Could not populate_db {} because {}".format(line, e))
                continue

            # append to populate_db queue
            nodes.append(d)

            if len(nodes) > 5000:
                batch_add_nodes(nodes, GwasInfo.get_node_label())
                nodes = []

    # add remaining nodes
    batch_add_nodes(nodes, GwasInfo.get_node_label())

    # populate_db groups
    logging.info("importing groups")
    with open('populate_db/data/groups.tsv') as f:
        for line in f:
            fields = line.strip().split("\t")
            g = Group(name=str(fields[1]))
            g.create_node()

            # gid = name
            gid_to_name[int(fields[0])] = fields[1]

    # populate_db users
    logging.info("importing users")
    with open('populate_db/data/memberships.tsv') as f:
        for line in f:
            fields = line.strip().split("\t")
            email = str(fields[0]).lower()
            gid = int(fields[1])

            # TODO @ben -- there are 0 grp but no grp name
            if gid == 0:
                continue

            if email not in email_to_gid:
                email_to_gid[email] = set()

            # email = set(gid)
            email_to_gid[email].add(gid)

        for email in email_to_gid:
            group_names = set()
            for gid in email_to_gid[email]:
                group_names.add(gid_to_name[int(gid)])

            add_new_user(email, group_names=group_names)

    # link gwas to group
    # TODO @be -- some studies do not exist in study table but have permissions
    logging.info("importing permissions")
    with open('populate_db/data/permissions_e.tsv') as f:
        rels = []
        for line in f:
            fields = line.strip().split("\t")

            # store link
            d = dict(gwas_id=fields[1], grp_id=gid_to_name[int(fields[0])])

            # append to populate_db queue
            rels.append(d)

            if len(rels) > 5000:
                batch_add_rel(rels)
                rels = []

        # add remaining rels
        batch_add_rel(rels)

    # create me as user
    # add me to all GWAS groups for testing purposes
    # TODO drop statement
    groups = set()
    for it in gid_to_name:
        groups.add(gid_to_name[it])
    add_new_user('ml18692@bristol.ac.uk', groups)

    # set all gwas as QC passed
    tx = Neo4j.get_db()
    tx.run("MATCH (u:User {uid:\"ml18692@bristol.ac.uk\"}) "
           "MATCH (g:GwasInfo) WHERE NOT (g)-[:DID_QC]->(:User) "
           "CREATE (g)-[:DID_QC {epoch:1549379289.720649, comment:\"historic\", data_passed:True}]->(u)")
