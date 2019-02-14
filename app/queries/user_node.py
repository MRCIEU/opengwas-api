from queries.unique_node import UniqueNode
from schemas.user_node_schema import UserNodeSchema
from resources._neo4j import Neo4j


class User(UniqueNode):
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
            "MERGE (n:" + self.get_node_label() + " {" + self._UID_KEY + ":{uid}}) ON CREATE SET n.admin=False;",
            uid=self.get(self._UID_KEY)
        )
