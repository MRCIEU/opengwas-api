from resources._neo4j import Neo4j
from schemas.study_node_schema import StudyNodeSchema


def add_study(data):
    Neo4j.create_unique_node(StudyNodeSchema.LABEL, data['id'], data, uid_key='id')


def get_study(uid):
    return Neo4j.get_unique_node(StudyNodeSchema.LABEL, uid, uid_key='id')


def delete_study(uid):
    Neo4j.delete_unique_node(StudyNodeSchema.LABEL, uid, uid_key='id')
