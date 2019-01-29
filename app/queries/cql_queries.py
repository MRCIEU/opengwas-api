from resources._neo4j import Neo4j
from queries.user_node import User
from queries.gwas_info_node import GwasInfo
from queries.added_by_rel import AddedByRel
from queries.access_to_rel import AccessToRel
from queries.group_node import Group
from schemas.gwas_info_node_schema import GwasInfoNodeSchema
import time
import os

# TODO @Gib how are users added to the graph? Who decides?

"""Return all available GWAS summary datasets"""


def get_all_gwas_for_user(uid):
    gids = get_groups_for_user(uid)
    res = []
    tx = Neo4j.get_db()
    results = tx.run(
        "MATCH (g:Group)-[:ACCESS_TO]->(gi:GwasInfo) WHERE g.gid IN {gids} RETURN distinct(gi) as gi;",
        gids=list(gids)
    )
    for result in results:
        res.append(result['gi'])

    return res


def get_all_gwas_ids_for_user(uid):
    recs = []
    gids = get_groups_for_user(uid)

    tx = Neo4j.get_db()
    results = tx.run(
        "MATCH (g:Group)-[:ACCESS_TO]->(gi:GwasInfo) WHERE g.gid IN {gids} RETURN distinct(gi.id) as id;",
        gids=list(gids)
    )

    for result in results:
        recs.append(result['id'])

    return recs


def get_gwas_for_user(uid, gwasid):
    gids = get_groups_for_user(uid)
    schema = GwasInfoNodeSchema()

    tx = Neo4j.get_db()

    results = tx.run(
        "MATCH (g:Group)-[:ACCESS_TO]->(gi:GwasInfo {id:{gwasid}}) WHERE g.gid IN {gids} RETURN distinct(gi);",
        gids=list(gids),
        gwasid=gwasid
    )

    result = results.single()
    if result is None:
        raise LookupError("GwasInfo ID {} does not exist or you do not have the required access".format(gwasid))

    return schema.load(result['gi'])


def add_new_gwas(user_email, gwas_info_dict, group=1):
    # get new id
    gwas_info_dict['id'] = str(GwasInfo.get_next_numeric_id())

    # populate nodes
    user_node = User({"uid": user_email})
    gwas_info_node = GwasInfo(gwas_info_dict)
    added_by_rel = AddedByRel({'epoch': time.time()})
    access_to_rel = AccessToRel()

    # get group
    group_node = Group.get_node(group)

    # persist or update
    user_node.create_node()
    gwas_info_node.create_node()
    added_by_rel.create_rel(gwas_info_node, user_node)
    access_to_rel.create_rel(group_node, gwas_info_node)

    return gwas_info_dict['id']


def update_filename_and_path(uid, full_remote_file_path):
    if not os.path.exists(full_remote_file_path):
        raise FileNotFoundError("The GWAS file does not exist on this server: {}".format(full_remote_file_path))

    tx = Neo4j.get_db()
    tx.run(
        "MATCH (gi:GwasInfo {id:{uid}}) SET gi.filename={filename}, gi.path={path};",
        uid=uid,
        path=os.path.dirname(full_remote_file_path),
        filename=os.path.basename(full_remote_file_path)
    )


def delete_gwas(uid, gwasid):
    gids = get_groups_for_user(uid)

    tx = Neo4j.get_db()
    tx.run(
        "MATCH (g:Group)-[:ACCESS_TO]->(gi:GwasInfo {id:{gwasid}}) WHERE g.gid IN {gids} "
        "WITH distinct(gi) as gi "
        "OPTIONAL MATCH (gi)-[rel]-() "
        "DELETE rel, gi;",
        gids=list(gids),
        gwasid=gwasid
    )


""" Returns studies for a list of study identifiers (or all public if keyword 'snp_lookup' provided)  """


# TODO @Gib should this check for user permissions?
def study_info(study_list):
    res = []
    schema = GwasInfoNodeSchema()
    tx = Neo4j.get_db()

    if study_list == 'snp_lookup':
        results = tx.run(
            "MATCH (:Group {gid:{gid}})-[:ACCESS_TO]->(gi:GwasInfo) RETURN gi;",
            gid=int(1)
        )
        for result in results:
            res.append(schema.load(result['gi']))

        return res
    else:
        study_list_str = []
        for s in study_list:
            study_list_str.append(str(s))

        results = tx.run(
            "MATCH (gi:GwasInfo) WHERE gi.id IN {study_list} RETURN gi;",
            study_list=study_list_str
        )
        for result in results:
            res.append(schema.load(result['gi']))

        return res


""" Returns list of group identifiers for a given user email (will accept NULL) """


def get_groups_for_user(uid):
    gids = set()
    tx = Neo4j.get_db()
    results = tx.run(
        "MATCH (:User {uid:{uid}})-[:MEMBER_OF]->(g:Group) RETURN g.gid as gid;",
        uid=str(uid)
    )
    for result in results:
        gids.add(result['gid'])

    results = tx.run(
        "MATCH (g:Group {name:{name}}) RETURN g.gid as gid;",
        name=str('public')
    )
    for result in results:
        gids.add(result['gid'])

    return gids
