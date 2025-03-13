from flask_login import UserMixin
import time

from queries.unique_node import UniqueNode
from schemas.user_node_schema import UserNodeSchema
from resources.neo4j import Neo4j


class User(UniqueNode, UserMixin):
    _UID_KEY = 'uid'
    _SCHEMA = UserNodeSchema

    def create_node(self):
        partial_fields_sign_up = ['first_name', 'last_name']
        partial_fields_every_time = ['group', 'source']
        partial_fields_all = partial_fields_sign_up + partial_fields_every_time
        # map using schema; fail when violates
        d = self._SCHEMA().load(self, partial=partial_fields_all)

        if d.get(self._UID_KEY) is None:
            raise KeyError("You must provide a value for the unique key.")

        params_common = {
            'uid': self.get(self._UID_KEY),
            'uuid': self.get('uuid'),
            'created': int(time.time()),
            'last_signin': int(time.time()),
            'tags': ['trial']
        }

        params_specific_sign_up = {}
        params_specific_every_time = {}
        for field_name in partial_fields_sign_up:
            if field_name in self:
                params_specific_sign_up[field_name] = self.get(field_name)
        for field_name in partial_fields_every_time:
            if field_name in self:
                params_specific_every_time[field_name] = self.get(field_name)

        tx = Neo4j.get_db()
        tx.run(
            "MERGE (n:" + self.get_node_label() + " {" + self._UID_KEY + ": $uid}) " +
            "ON CREATE SET " + ','.join(['n.{}=${}'.format(f, f) for f in ['uuid'] + list(params_specific_sign_up.keys()) + list(params_specific_every_time.keys()) + ['created', 'last_signin', 'tags']]) + " " +
            "ON MATCH SET " + ','.join(['n.{}=${}'.format(f, f) for f in list(params_specific_every_time.keys()) + ['last_signin']]) + ";",
            parameters={**params_common, **params_specific_sign_up, **params_specific_every_time}
        )

    def set_jwt_timestamp(self, uid, timestamp):
        self._SCHEMA().load(self, partial=True)
        Neo4j.get_db().run(
            "MATCH (n:" + self.get_node_label() + " {" + self._UID_KEY + ": $uid}) SET n.jwt_timestamp=$timestamp;",
            uid=uid, timestamp=timestamp
        )

    def set_names(self, uid, first_name, last_name):
        self._SCHEMA().load(self, partial=True)
        Neo4j.get_db().run(
            "MATCH (n:" + self.get_node_label() + " {" + self._UID_KEY + ": $uid}) SET n.first_name=$first_name, n.last_name=$last_name;",
            uid=uid, first_name=first_name, last_name=last_name
        )

    # Overwrites UserMixin.get_id()
    def get_id(self):
        return str(self[self._UID_KEY])

    def is_blocked(self):
        return int(self.get('blocked_until', 0)) > int(time.time())
