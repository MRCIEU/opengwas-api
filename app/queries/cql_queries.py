from resources.neo4j import Neo4j
from queries.user_node import User
from queries.gwas_info_node import GwasInfo
from queries.added_by_rel import AddedByRel
from queries.quality_control_rel import QualityControlRel
from queries.access_to_rel import AccessToRel
from queries.member_of_rel import MemberOfRel
from queries.group_node import Group
from schemas.gwas_info_node_schema import GwasInfoNodeSchema
import time

"""Return all available GWAS summary datasets"""


def get_all_gwas_for_user(uid):
    group_names = get_groups_for_user(uid)
    res = {}
    tx = Neo4j.get_db()
    results = tx.run(
        "MATCH (g:Group)-[:ACCESS_TO]->(gi:GwasInfo)-[:DID_QC {data_passed:True}]->(:User) WHERE g.name IN {group_names} RETURN distinct(gi) as gi;",
        group_names=list(group_names)
    )
    for result in results:
        res[result['gi']['id']] = GwasInfo(result['gi'])

    return res


def get_all_gwas_ids_for_user(uid):
    recs = []
    group_names = get_groups_for_user(uid)

    tx = Neo4j.get_db()
    results = tx.run(
        "MATCH (g:Group)-[:ACCESS_TO]->(gi:GwasInfo)-[:DID_QC {data_passed:True}]->(:User) WHERE g.name IN {group_names} RETURN distinct(gi.id) as id;",
        group_names=list(group_names)
    )

    for result in results:
        recs.append(result['id'])

    return recs


def get_gwas_for_user(uid, gwasid, datapass=True):
    group_names = get_groups_for_user(uid)
    schema = GwasInfoNodeSchema()

    tx = Neo4j.get_db()

    if datapass:
        results = tx.run(
            "MATCH (g:Group)-[:ACCESS_TO]->(gi:GwasInfo {id:{gwasid}})-[:DID_QC {data_passed:True}]->(:User) WHERE g.name IN {group_names} RETURN distinct(gi);",
            group_names=list(group_names),
            gwasid=gwasid
        )
    else:
        results = tx.run(
            "MATCH (g:Group)-[:ACCESS_TO]->(gi:GwasInfo {id:{gwasid}}) WHERE g.name IN {group_names} RETURN distinct(gi);",
            group_names=list(group_names),
            gwasid=gwasid
        )

    result = results.single()
    if result is None:
        raise LookupError("GwasInfo ID {} does not exist or you do not have the required access".format(gwasid))

    return schema.load(GwasInfo(result['gi']))


def add_new_gwas(user_email, gwas_info_dict, group_names=frozenset(['public']), gwas_id=None):
    if gwas_id is not None:
        try:
            GwasInfo.get_node(str(gwas_id))
            raise ValueError("Identifier has already been taken")
        except LookupError:
            # check node does not already exist
            gwas_info_dict['id'] = str(gwas_id)
    else:
        # get new id
        gwas_info_dict['id'] = str(GwasInfo.get_next_numeric_id())

    # populate nodes
    gwas_info_node = GwasInfo(gwas_info_dict)
    added_by_rel = AddedByRel({'epoch': time.time()})
    access_to_rel = AccessToRel()

    # persist or update
    gwas_info_node.create_node()
    added_by_rel.create_rel(gwas_info_node, User.get_node(user_email))

    # add grps
    for group_name in group_names:
        group_node = Group.get_node(group_name)
        access_to_rel.create_rel(group_node, gwas_info_node)

    return gwas_info_dict['id']


def edit_existing_gwas(gwas_id, gwas_info_dict):
    try:
        GwasInfo.get_node(str(gwas_id))
    except LookupError:
        raise ValueError("Identifier does not exist")

    gwas_info_dict['id'] = str(gwas_id)

    # populate nodes
    # gwas_info_dict['priority'] = 0
    gwas_info_node = GwasInfo(gwas_info_dict)
    gwas_info_node.edit_node()

    # update grps
    if gwas_info_dict['group_name'] is not None:
        delete_groups(gwas_id)
        group_node = Group.get_node(gwas_info_dict['group_name'])
        access_to_rel = AccessToRel()
        access_to_rel.create_rel(group_node, gwas_info_node)

    return gwas_info_dict['id']


def add_new_user(email, group_names=frozenset(['public']), admin=False):
    uid = email.strip().lower()
    member_of_rel = MemberOfRel()
    u = User(uid=uid)
    u.create_node()

    if admin:
        User.set_admin(uid)

    for group_name in group_names:
        g = Group.get_node(group_name)
        member_of_rel.create_rel(u, g)


def add_group_to_user(email, group_name):
    member_of_rel = MemberOfRel()
    u = User.get_node(email)
    g = Group.get_node(group_name)
    member_of_rel.create_rel(u, g)


def delete_gwas(gwasid):
    tx = Neo4j.get_db()
    tx.run(
        "MATCH (gi:GwasInfo {id:{gwasid}}) "
        "OPTIONAL MATCH (gi)-[rel]-() "
        "DELETE rel, gi;",
        gwasid=gwasid
    )


def delete_groups(gwasid):
    tx = Neo4j.get_db()
    tx.run(
        "MATCH (gi:GwasInfo {id:{gwasid}})-[rel]-(g:Group) "
        "DELETE rel;",
        gwasid=gwasid
    )

""" Returns list of group identifiers for a given user email (will accept None) """


def get_groups_for_user(uid):
    if uid is None:
        return {'public'}

    names = set()
    names.add('public')

    tx = Neo4j.get_db()
    results = tx.run(
        "MATCH (:User {uid:{uid}})-[:MEMBER_OF]->(g:Group) RETURN g.name as name;",
        uid=str(uid)
    )
    for result in results:
        names.add(result['name'])

    return names


""" Get GwasInfo from list of studies given user permission"""


def get_permitted_studies(uid, gwas_info_ids: list):
    assert isinstance(gwas_info_ids, list)
    gwas_info_ids_str = []
    for i in gwas_info_ids:
        gwas_info_ids_str.append(str(i))
    schema = GwasInfoNodeSchema()
    group_names = get_groups_for_user(uid)
    tx = Neo4j.get_db()
    results = tx.run(
        "MATCH (g:Group)-[:ACCESS_TO]->(s:GwasInfo)-[:DID_QC {data_passed:True}]->(:User) WHERE g.name IN {group_names} AND s.id IN {sid} RETURN distinct(s) as s;",
        group_names=list(group_names), sid=gwas_info_ids_str
    )
    res = {}
    for result in results:
        res[result['s']['id']] = schema.load(result['s'])
    return res


def add_quality_control(user_email, gwas_info_id, data_passed, comment=None):
    u = User.get_node(user_email)
    g = GwasInfo.get_node(gwas_info_id)
    r = QualityControlRel(epoch=time.time(), data_passed=data_passed, comment=comment)

    # create QC rel
    r.create_rel(g, u)


def delete_quality_control(gwas_info_id):
    tx = Neo4j.get_db()
    tx.run(
        "MATCH (gi:GwasInfo {id:{uid}})-[r:DID_QC]->(:User) DELETE r;",
        uid=str(gwas_info_id)
    )


def check_user_is_admin(uid):
    try:
        u = User.get_node(uid)
    except LookupError:
        raise PermissionError("The token must resolve to a valid user")
    if 'admin' not in u:
        raise PermissionError("You must be an admin to complete this function")
    if ['admin'] != "true":
        raise PermissionError("You must be an admin to complete this function")


def get_todo_quality_control():
    res = []
    tx = Neo4j.get_db()
    results = tx.run(
        "MATCH (gi:GwasInfo) WHERE NOT (gi)-[:DID_QC]->(:User) RETURN gi;"
    )
    for result in results:
        res.append(GwasInfo(result['gi']))

    return res
