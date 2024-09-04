import neo4j.debug
from flask_login import UserMixin
import time

from queries.unique_node import UniqueNode
from schemas.user_node_schema import UserNodeSchema
from resources.neo4j import Neo4j


class User(UniqueNode, UserMixin):
    _UID_KEY = 'uid'
    _SCHEMA = UserNodeSchema

    def create_node(self):
        partial_fields = ['first_name', 'last_name', 'tier', 'source']
        # map using schema; fail when violates
        schema = self._SCHEMA()
        d = schema.load(self, partial=partial_fields)

        if d.get(self._UID_KEY) is None:
            raise KeyError("You must provide a value for the unique key.")

        params_common = {
            'uid': self.get(self._UID_KEY),
            'uuid': self.get('uuid'),
            'created': int(time.time()),
            'last_signin': int(time.time())
        }

        params_specific = {}
        for field_name in partial_fields:
            if field_name in self:
                params_specific[field_name] = self.get(field_name)

        tx = Neo4j.get_db()
        tx.run(
            "MERGE (n:" + self.get_node_label() + " {" + self._UID_KEY + ": $uid}) " +
            "ON CREATE SET " + ','.join(['n.{}=${}'.format(f, f) for f in ['uuid'] + list(params_specific.keys()) + ['created', 'last_signin']]) + " " +
            "ON MATCH SET " + ','.join(['n.{}=${}'.format(f, f) for f in list(params_specific.keys()) + ['last_signin']]) + ";",
            parameters={**params_common, **params_specific}
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
