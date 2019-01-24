from resources._neo4j import Neo4j
from schemas.study_node_schema import StudyNodeSchema

"""Return all available GWAS summary datasets"""


def get_all_gwas(uid):
    schema = StudyNodeSchema()
    gids = get_groups_for_user(uid)
    res = []
    tx = Neo4j.get_db()
    results = tx.run(
        "MATCH (g:Group)-[:ACCESS_TO]->(s:Study) WHERE g.gid IN {gids} RETURN distinct(s) as s;",
        gids=list(gids)
    )
    for result in results:
        res.append(schema.load(result['s']))

    return res


def get_all_gwas_ids(uid):
    recs = []
    gids = get_groups_for_user(uid)

    tx = Neo4j.get_db()
    results = tx.run(
        "MATCH (g:Group)-[:ACCESS_TO]->(s:Study) WHERE g.gid IN {gids} RETURN distinct(s.id) as id;",
        gids=list(gids)
    )

    for result in results:
        recs.append(result['id'])

    return recs


def get_specific_gwas(uid, sid):
    schema = StudyNodeSchema()
    gids = get_groups_for_user(uid)

    tx = Neo4j.get_db()

    results = tx.run(
        "MATCH (g:Group)-[:ACCESS_TO]->(s:Study {id:{sid}}) WHERE g.gid IN {gids} RETURN distinct(s);",
        gids=list(gids),
        sid=sid
    )

    result = results.single()
    if result is None:
        raise LookupError("Study ID {} does not exist or you do not have the required access".format(sid))

    return schema.load(result['s'])


""" Returns studies for a list of study identifiers (or all public if keyword 'snp_lookup' provided)  """


def study_info(study_list):
    res = []
    schema = StudyNodeSchema()
    tx = Neo4j.get_db()

    if study_list == 'snp_lookup':
        results = tx.run(
            "MATCH (:Group {gid:{gid}})-[:ACCESS_TO]->(s:Study) RETURN s;",
            gid=int(1)
        )
        for result in results:
            res.append(schema.load(result['s']))

        return res
    else:
        study_list_str = []
        for s in study_list:
            study_list_str.append(str(s))

        results = tx.run(
            "MATCH (s:Study) WHERE s.id IN {study_list} RETURN s;",
            study_list=study_list_str
        )
        for result in results:
            res.append(schema.load(result['s']))

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
