from resources.neo4j import Neo4j
from schemas.unique_node_schema import UniqueNodeSchema


class UniqueNode(dict):
    _UID_KEY = 'uid'
    _SCHEMA = UniqueNodeSchema

    @classmethod
    def get_next_numeric_id(cls):
        tx = Neo4j.get_db()
        results = tx.run(
            "MATCH (n:" + cls.get_node_label() + ") RETURN max(toInteger(n." + cls._UID_KEY + ")) + 1 as uid;"
        )
        return results.single()['uid']

    def get_uid(self):
        return self[self._UID_KEY]

    @classmethod
    def get_uid_key(cls):
        return cls._UID_KEY

    def create_node(self):
        # map using schema; fail when violates
        schema = self._SCHEMA()
        d = schema.load(self)

        if d.get(self._UID_KEY) is None:
            raise KeyError("You must provide a value for the unique key.")

        tx = Neo4j.get_db()
        tx.run(
            "MERGE (n:" + self.get_node_label() + " {" + self._UID_KEY + ": '" + self._UID_KEY + "'}) SET n += $params;",
            params=d
        )
    
    def edit_node(self):
        schema = self._SCHEMA()
        d = schema.load(self)
        tx = Neo4j.get_db()
        tx.run(
            "MATCH (n:" + self.get_node_label() + " {" + self._UID_KEY + ": '" + self._UID_KEY + "'}) "
            "SET n = $params;",
            params=d
        )

    @classmethod
    def delete_node(cls, uid):
        if uid is None:
            raise KeyError("You must provide a value for the unique key.")
        tx = Neo4j.get_db()
        tx.run(
            "MATCH (n:" + cls.get_node_label() + " {" + cls._UID_KEY + ": '" + uid + "'}) OPTIONAL MATCH (n)-[r]-() DELETE n, r;"
        )

    @classmethod
    def get_node(cls, uid):
        if uid is None:
            raise KeyError("You must provide a value for the unique key.")

        tx = Neo4j.get_db()
        results = tx.run(
            "MATCH (n:" + cls.get_node_label() + " {" + cls._UID_KEY + ": '" + uid + "'}) RETURN n;"
        )
        result = results.single()

        if result is None:
            raise LookupError("Node does not exist for: {}".format(uid))

        # instantiate schema belonging to subclass
        schema = cls._SCHEMA()

        # map node data to dict using schema; fail when violates
        d = schema.load(result['n'])

        # return instance of populated subclass
        return cls(**d)

    @classmethod
    def set_constraint(cls):
        tx = Neo4j.get_db()
        tx.run(
            "CREATE CONSTRAINT FOR (n:" + cls.get_node_label() + ") REQUIRE n." + cls._UID_KEY + " IS UNIQUE;"
        )

    @classmethod
    def drop_constraint(cls):
        tx = Neo4j.get_db()
        constraints = tx.run(
            "SHOW CONSTRAINTS WHERE labelsOrTypes = [\"" + cls.get_node_label() + "\"];"
        )
        for c in constraints:
            tx.run(
                "DROP CONSTRAINT " + c['name'] + ";"
            )

    @classmethod
    def check_constraint(cls):
        labels = set()
        tx = Neo4j.get_db()
        results = tx.run(
            "SHOW INDEXES WHERE properties IS NOT NULL;"
        )
        for result in results:
            if cls._UID_KEY in result['properties']:
                for l in result['labelsOrTypes']:
                    labels.add(l)
        return cls.get_node_label() in labels

    @classmethod
    def get_node_label(cls):
        return str(cls.__name__)
