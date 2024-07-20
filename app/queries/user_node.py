from flask_login import UserMixin
import time

from queries.unique_node import UniqueNode
from schemas.user_node_schema import UserNodeSchema
from resources.neo4j import Neo4j


class User(UniqueNode, UserMixin):
    _UID_KEY = 'uid'
    _SCHEMA = UserNodeSchema

    def create_node(self):
        # map using schema; fail when violates
        schema = self._SCHEMA()
        d = schema.load(self)

        if d.get(self._UID_KEY) is None:
            raise KeyError("You must provide a value for the unique key.")

        tx = Neo4j.get_db()
        tx.run(
            "MERGE (n:" + self.get_node_label() + " {" + self._UID_KEY + ": $uid}) " +
            "ON CREATE SET n.first_name=$first_name, n.last_name=$last_name, n.tier=$tier, n.source=$source, n.created=$timestamp " +
            "ON MATCH SET n.first_name=$first_name, n.last_name=$last_name, n.tier=$tier, n.source=$source, n.updated=$timestamp;",
            uid=self.get(self._UID_KEY),
            first_name=d['first_name'], last_name=d['last_name'], tier=d['tier'], source=d['source'], timestamp=int(time.time())
        )

    @classmethod
    def set_jwt_timestamp(cls, uid, timestamp):
        tx = Neo4j.get_db()
        tx.run(
            "MATCH (n:" + cls.get_node_label() + " {" + cls._UID_KEY + ": $uid}) SET n.jwt_timestamp=$timestamp;",
            uid=uid, timestamp=timestamp
        )

    @classmethod
    def set_names(cls, uid, first_name, last_name):
        tx = Neo4j.get_db()
        tx.run(
            "MATCH (n:" + cls.get_node_label() + " {" + cls._UID_KEY + ": $uid}) SET n.first_name=$first_name, n.last_name=$last_name;",
            uid=uid, first_name=first_name, last_name=last_name
        )

    # Overwrites UserMixin.get_id()
    def get_id(self):
        return str(self[self._UID_KEY])
