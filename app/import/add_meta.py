from queries.group_node import Group
from queries.user_node import User
import flask
import logging
from resources._neo4j import Neo4j
from queries.access_to_rel import AccessToRel
from queries.gwas_info_node import GwasInfo
from queries.cql_queries import add_new_user

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

# import to neo4
app = flask.Flask(__name__)
app.teardown_appcontext(Neo4j.close_db)

with app.app_context():
    Group.set_constraint()
    User.set_constraint()
    access_to_rel = AccessToRel()

    gid_to_name = dict()
    email_to_gid = dict()

    # import groups
    with open('import/data/groups.tsv') as f:
        for line in f:
            fields = line.strip().split("\t")
            g = Group(name=str(fields[1]))
            g.create_node()

            # gid = name
            gid_to_name[int(fields[0])] = fields[1]

    # import users
    with open('import/data/memberships.tsv') as f:
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
    with open('import/data/permissions_e.tsv') as f:
        tx = Neo4j.get_db()
        for line in f:
            fields = line.strip().split("\t")

            tx.run("MATCH (gi:GwasInfo) where gi.id = {gwas_id} "
                   "MATCH (grp:Group) where grp.name = {grp_id} "
                   "MERGE (grp)-[:ACCESS_TO]->(gi);", gwas_id=fields[1], grp_id=gid_to_name[int(fields[0])])
