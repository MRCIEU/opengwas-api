from resources._globals import *
from resources._logger import *
import flask


class Neo4j:

    @staticmethod
    def close_db(error):
        logging.info("Closing neo4j session")
        if hasattr(flask.g, 'neo4j_db'):
            flask.g.neo4j_db.close()

    @staticmethod
    def get_db():
        if not hasattr(flask.g, 'neo4j_db'):
            flask.g.neo4j_db = dbConnection.session()
        return flask.g.neo4j_db

    @staticmethod
    def clear_db():
        tx = Neo4j.get_db()
        tx.run("MATCH (n) OPTIONAL MATCH (n)-[r]-() DELETE n,r;")

    @staticmethod
    def check_running():
        try:
            tx = Neo4j.get_db()
            tx.run("MATCH (n) RETURN n LIMIT 0;")
        except Exception:
            return 'Unavailable'
        return 'Available'

    @staticmethod
    def create_unique_rel(rel_type, lhs_label, lhs_uid, rhs_label, rhs_uid, rel_props=None, lhs_uid_key='uid',
                          rhs_uid_key='uid'):
        tx = Neo4j.get_db()
        tx.run(
            "MATCH (l:{lhs_label}:{{lhs_uid_key}:{lhs_uid}} "
            "MATCH (r:{rhs_label}:{{rhs_uid_key}:{rhs_uid}} "
            "MERGE (l)-[r:{rel_type}]->(r) "
            "SET r = {rel_props};",
            lhs_label=lhs_label,
            lhs_uid_key=lhs_uid_key,
            lhs_uid=lhs_uid,
            rhs_label=rhs_label,
            rhs_uid_key=rhs_uid_key,
            rhs_uid=rhs_uid,
            rel_type=rel_type,
            rel_props=rel_props
        )

    @staticmethod
    def delete_rel(rel_type, lhs_label, lhs_uid, rhs_label, rhs_uid, lhs_uid_key='uid', rhs_uid_key='uid'):
        tx = Neo4j.get_db()
        tx.run(
            "MATCH (l:{lhs_label}:{{lhs_uid_key}:{lhs_uid}}-[r:{rel_type}]->(r:{rhs_label}:{{rhs_uid_key}:{rhs_uid}}"
            "DELETE (r);",
            lhs_label=lhs_label,
            lhs_uid_key=lhs_uid_key,
            lhs_uid=lhs_uid,
            rhs_label=rhs_label,
            rhs_uid_key=rhs_uid_key,
            rhs_uid=rhs_uid,
            rel_type=rel_type
        )

    @staticmethod
    def create_unique_node(label, uid, props=None, uid_key='uid'):
        cql = "MERGE (n:" + label + " {" + uid_key + ":{uid}})"
        if props is not None:
            cql += "SET n = {params}"
        cql += "SET n." + uid_key + " = {uid};"
        tx = Neo4j.get_db()
        tx.run(
            cql, uid=uid, params=props
        )

    @staticmethod
    def delete_unique_node(label, uid, uid_key='uid'):
        tx = Neo4j.get_db()
        tx.run(
            "MATCH (n:" + label + " {" + uid_key + ":{uid}}) OPTIONAL MATCH (n)-[r]-() DELETE n, r;",
            uid=uid
        )

    @staticmethod
    def get_unique_node(label, uid, uid_key='uid'):
        tx = Neo4j.get_db()
        results = tx.run(
            "MATCH (n:" + label + " {" + uid_key + ":{uid}}) RETURN n;",
            uid=uid
        )
        result = results.single()

        if result is None:
            raise LookupError("Node does not exist for: {}".format(uid))

        return result['n']

    @staticmethod
    def set_constraint(label, prop):
        tx = Neo4j.get_db()
        tx.run(
            "CREATE CONSTRAINT ON (n:" + label + ") ASSERT n." + prop + " IS UNIQUE;"
        )

    @staticmethod
    def check_constraint(label, prop):
        labels = set()
        tx = Neo4j.get_db()
        results = tx.run(
            "CALL db.indexes();"
        )
        for result in results:
            if prop in result['properties']:
                labels.add(result['label'])
        return label in labels
