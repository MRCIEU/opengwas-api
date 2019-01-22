from resources._neo4j import Neo4j


# TODO
class UniqueNode(dict):
    _UID_KEY = 'uid'

    def create_node(self):
        tx = Neo4j.get_db()
        tx.run(
            "MERGE (n:" + str(self.__class__.__name__) + " {" + self._UID_KEY + ":{uid}}) SET n = {params};",
            uid=self.get(self._UID_KEY),
            params=self.items()
        )

    @classmethod
    def delete_node(cls, uid):
        tx = Neo4j.get_db()
        tx.run(
            "MATCH (n:" + str(cls.__name__) + " {" + cls._UID_KEY + ":{uid}}) OPTIONAL MATCH (n)-[r]-() DELETE n, r;",
            uid=uid
        )

    @classmethod
    def get_node(cls, uid):
        tx = Neo4j.get_db()
        results = tx.run(
            "MATCH (n:" + str(cls.__name__) + " {" + cls._UID_KEY + ":{uid}}) RETURN n;",
            uid=uid
        )
        result = results.single()

        if result is None:
            raise LookupError("Node does not exist for: {}".format(uid))

        # TODO return class obj
        return result['n']

    @classmethod
    def set_constraint(cls):
        tx = Neo4j.get_db()
        tx.run(
            "CREATE CONSTRAINT ON (n:" + str(cls.__name__) + ") ASSERT n." + cls._UID_KEY + " IS UNIQUE;"
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
        return str(cls.__name__) in labels
