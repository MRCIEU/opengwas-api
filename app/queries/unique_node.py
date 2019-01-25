from resources._neo4j import Neo4j
from schemas.unique_node_schema import UniqueNodeSchema


# TODO param cql
class UniqueNode(dict):
    _UID_KEY = 'uid'
    _SCHEMA = UniqueNodeSchema

    def get_uid(self):
        return self[self._UID_KEY]

    def get_uid_key(self):
        return self._UID_KEY

    def create_node(self):
        tx = Neo4j.get_db()
        tx.run(
            "MERGE (n:" + self.get_node_label() + " {" + self._UID_KEY + ":{uid}}) SET n = {params};",
            uid=self.get(self._UID_KEY),
            params=self
        )

    @classmethod
    def delete_node(cls, uid):
        tx = Neo4j.get_db()
        tx.run(
            "MATCH (n:" + cls.get_node_label() + " {" + cls._UID_KEY + ":{uid}}) OPTIONAL MATCH (n)-[r]-() DELETE n, r;",
            uid=uid
        )

    @classmethod
    def get_node(cls, uid):

        tx = Neo4j.get_db()
        results = tx.run(
            "MATCH (n:" + cls.get_node_label() + " {" + cls._UID_KEY + ":{uid}}) RETURN n;",
            uid=uid
        )
        result = results.single()

        if result is None:
            raise LookupError("Node does not exist for: {}".format(uid))

        # instantiate schema belonging to subclass
        schema = cls._SCHEMA()

        # map node data to dict using schema; fail when violates
        d = schema.load(result['n'])

        # return instance of populated subclass
        return cls(d)

    @classmethod
    def set_constraint(cls):
        tx = Neo4j.get_db()
        tx.run(
            "CREATE CONSTRAINT ON (n:" + cls.get_node_label() + ") ASSERT n." + cls._UID_KEY + " IS UNIQUE;"
        )

    @classmethod
    def drop_constraint(cls):
        tx = Neo4j.get_db()
        tx.run(
            "DROP CONSTRAINT ON (n:" + cls.get_node_label() + ") ASSERT n." + cls._UID_KEY + " IS UNIQUE;"
        )

    @classmethod
    def check_constraint(cls):
        labels = set()
        tx = Neo4j.get_db()
        results = tx.run(
            "CALL db.indexes();"
        )
        for result in results:
            if cls._UID_KEY in result['properties']:
                labels.add(result['label'])
        return cls.get_node_label() in labels

    @classmethod
    def get_node_label(cls):
        return str(cls.__name__)
