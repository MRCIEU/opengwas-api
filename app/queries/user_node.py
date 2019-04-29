from queries.unique_node import UniqueNode
from schemas.user_node_schema import UserNodeSchema
from resources.neo4j import Neo4j


class User(UniqueNode):
    _UID_KEY = 'uid'
    _SCHEMA = UserNodeSchema

    @classmethod
    def set_admin(cls, uid):
        tx = Neo4j.get_db()
        tx.run(
            "MATCH (n:" + cls.get_node_label() + " {" + cls._UID_KEY + ":{uid}}) SET n.admin=True;",
            uid=uid
        )

    def create_node(self):
        # map using schema; fail when violates
        schema = self._SCHEMA()
        d = schema.load(self)

        if d.get(self._UID_KEY) is None:
            raise KeyError("You must provide a value for the unique key.")

        tx = Neo4j.get_db()
        tx.run(
            "MERGE (n:" + self.get_node_label() + " {" + self._UID_KEY + ":{uid}}) ON CREATE SET n.admin=False;",
            uid=self.get(self._UID_KEY)
        )
