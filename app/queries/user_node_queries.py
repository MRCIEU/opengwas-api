from resources._neo4j import Neo4j
from schemas.user_node_schema import UserNodeSchema


def add_user(uid):
    Neo4j.create_unique_node(UserNodeSchema.LABEL, uid)


def get_user(uid):
    return Neo4j.get_unique_node(UserNodeSchema.LABEL, uid)


def delete_user(uid):
    Neo4j.delete_unique_node(UserNodeSchema.LABEL, uid)
