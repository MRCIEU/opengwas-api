from resources.neo4j import Neo4j
from schemas.unique_rel_schema import UniqueRelSchema


class UniqueRel(dict):
    _TYPE = "UNIQUE_REL"
    _SCHEMA = UniqueRelSchema

    def create_rel(self, lhs_node, rhs_node):
        if lhs_node is None:
            raise KeyError("You must provide a value for the left node.")
        if rhs_node is None:
            raise KeyError("You must provide a value for the right node.")

        tx = Neo4j.get_db()
        tx.run(
            "MATCH (l:" + lhs_node.get_node_label() + " {" + lhs_node.get_uid_key() + ":'" + lhs_node.get_uid() + "'}) "
            "MATCH (r:" + rhs_node.get_node_label() + " {" + rhs_node.get_uid_key() + ":'" + rhs_node.get_uid() + "'}) "
            "MERGE (l)-[rel:" + self.get_rel_type() + "]->(r) "
            "SET rel = " + str(self) + ";"
        )

    @classmethod
    def delete_rel(cls, lhs_node, rhs_node):
        if lhs_node is None:
            raise KeyError("You must provide a value for the left node.")
        if rhs_node is None:
            raise KeyError("You must provide a value for the right node.")

        tx = Neo4j.get_db()
        tx.run(
            "MATCH (l:" + lhs_node.get_node_label() + " {" + lhs_node.get_uid_key() + ":$lhs_uid})-[rel:" + cls.get_rel_type() + "]-(r:" + rhs_node.get_node_label() + " {" + rhs_node.get_uid_key() + ":$rhs_uid})"
            "DELETE (rel);",
            lhs_uid=lhs_node.get_uid(),
            rhs_uid=rhs_node.get_uid(),
            rel_type=cls.get_rel_type()
        )

    @classmethod
    def get_rel_props(cls, lhs_node, rhs_node):
        if lhs_node is None:
            raise KeyError("You must provide a value for the left node.")
        if rhs_node is None:
            raise KeyError("You must provide a value for the right node.")

        tx = Neo4j.get_db()
        results = tx.run(
            "MATCH (l:" + lhs_node.get_node_label() + " {" + lhs_node.get_uid_key() + ":$lhs_uid})-[rel:" + cls.get_rel_type() + "]-(r:" + rhs_node.get_node_label() + " {" + rhs_node.get_uid_key() + ":$rhs_uid})"
            "RETURN rel;",
            lhs_uid=lhs_node.get_uid(),
            rhs_uid=rhs_node.get_uid(),
            rel_type=cls.get_rel_type()
        )
        result = results.single()

        if result is None:
            raise LookupError("Relationship does not exist")

        # instantiate schema belonging to subclass
        schema = cls._SCHEMA()

        # map node data to dict using schema; fail when violates
        d = schema.load(result['rel'])

        # return instance of populated subclass
        return cls(d)

    @classmethod
    def get_rel_type(cls):
        return str(cls._TYPE)
