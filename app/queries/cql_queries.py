from resources._neo4j import Neo4j
from schemas.study_node_schema import StudyNodeSchema

"""Return all available GWAS summary datasets"""


def get_all_gwas(uid):
    schema = StudyNodeSchema()
    res = []
    tx = Neo4j.get_db()
    results = tx.run(
        "MATCH (:User {uid:{uid}})-[:MEMBER_OF]->(:Group)-[:ACCESS_TO]->(s:Study) RETURN s;",
        uid=uid
    )
    for result in results:
        res.append(schema.load(result['s']))

    return res


def get_all_gwas_ids(uid):
    recs = []
    tx = Neo4j.get_db()
    results = tx.run(
        "MATCH (:User {uid:{uid}})-[:MEMBER_OF]->(:Group)-[:ACCESS_TO]->(s:Study) RETURN distinct(s.id) as id;",
        uid=uid
    )
    for result in results:
        recs.append(result['id'])

    return recs


def get_specific_gwas(uid, sid):
    schema = StudyNodeSchema()
    tx = Neo4j.get_db()
    results = tx.run(
        "MATCH (:User {uid:{uid}})-[:MEMBER_OF]->(:Group)-[:ACCESS_TO]->(s:Study {id:{sid}}) RETURN s;",
        uid=uid,
        sid=sid
    )
    result = results.single()
    if result is None:
        raise LookupError("Study ID {} does not exist or you do not have the required permissions".format(sid))
    return schema.load(result['s'])


def study_info(study_list):
    res = []
    schema = StudyNodeSchema()
    tx = Neo4j.get_db()

    if study_list == 'snp_lookup':
        results = tx.run(
            "MATCH (:Group {gid:{gid}})-[:ACCESS_TO]->(s:Study) RETURN s;",
            gid=1
        )
        for result in results:
            res.append(schema.load(result['s']))

        return res
    else:
        results = tx.run(
            "MATCH (s:Study) WHERE s.id IN study_list RETURN s;",
            study_list=study_list
        )
        for result in results:
            res.append(schema.load(result['s']))

        return res
