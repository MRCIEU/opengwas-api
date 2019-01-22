from resources._neo4j import Neo4j
from schemas.access_to_rel_schema import AccessToRelSchema
from schemas.group_node_schema import GroupNodeSchema

# TODO




def add_rel(data):
    Neo4j.create_unique_rel(AccessToRelSchema.REL, GroupNodeSchema.LABEL, )


def get_study(uid):
    return Neo4j.get_unique_node(StudyNodeSchema.LABEL, uid, uid_key='id')


def delete_study(uid):
    Neo4j.delete_unique_node(StudyNodeSchema.LABEL, uid, uid_key='id')
