from resources._neo4j import Neo4j
from schemas.gwas_info_node_schema import GwasInfoNodeSchema

# TODO @Gib how are users added to the graph? Who decides?

"""Return all available GWAS summary datasets"""


def get_all_gwas(uid):
    schema = GwasInfoNodeSchema()
    gids = get_groups_for_user(uid)
    res = []
    tx = Neo4j.get_db()
    results = tx.run(
        "MATCH (g:Group)-[:ACCESS_TO]->(gi:GwasInfo) WHERE g.gid IN {gids} RETURN distinct(gi) as gi;",
        gids=list(gids)
    )
    for result in results:
        res.append(schema.load(result['gi']))

    return res


def get_permitted_studies(uid, gwasid):
    schema = GwasInfoNodeSchema()
    gids = get_groups_for_user(uid)
    tx = Neo4j.get_db()
    results = tx.run(
        "MATCH (g:Group)-[:ACCESS_TO]->(gi:GwasInfo) WHERE g.gid IN {gids} AND gi.id IN {gwasid} RETURN distinct(gi) as gi;",
        gids=list(gids), gwasid=list(gwasid)
    )
    res = []
    for result in results:
        res.append(schema.load(result['gi']))
    return res


def get_all_gwas_ids(uid):
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


def get_specific_gwas(uid, gwasid):
    schema = GwasInfoNodeSchema()
    gids = get_groups_for_user(uid)

    tx = Neo4j.get_db()

    results = tx.run(
        "MATCH (g:Group)-[:ACCESS_TO]->(gi:GwasInfo {id:{gwasid}}) WHERE g.gid IN {gids} RETURN distinct(gi);",
        gids=list(gids),
        gwasid=gwasid
    )

    result = results.single()
    if result is None:
        raise LookupError("Study ID {} does not exist or you do not have the required access".format(gwasid))

    return schema.load(result['gi'])


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
