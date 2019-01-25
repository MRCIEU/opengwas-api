from resources._neo4j import Neo4j
from schemas.unique_rel_schema import UniqueRelSchema


class UniqueRel(dict):
    _SCHEMA = UniqueRelSchema

    def create_rel(self, lhs_node, rhs_node):
        tx = Neo4j.get_db()
        tx.run(
            "MATCH (l:{lhs_label}:{{lhs_uid_key}:{lhs_uid}}) "
            "MATCH (r:{rhs_label}:{{rhs_uid_key}:{rhs_uid}}) "
            "MERGE (l)-[r:{rel_type}]->(r) "
            "SET r = {rel_props};",
            lhs_label=lhs_node.get_node_label(),
            lhs_uid_key=lhs_node.get_uid_key(),
            lhs_uid=lhs_node.get_uid(),
            rhs_label=rhs_node.get_node_label(),
            rhs_uid_key=rhs_node.get_uid_key(),
            rhs_uid=rhs_node.get_uid(),
            rel_type=self.get_rel_type(),
            rel_props=self
        )

    @classmethod
    def delete_rel(cls, lhs_node, rhs_node):
        tx = Neo4j.get_db()
        tx.run(
            "MATCH (l:{lhs_label}:{{lhs_uid_key}:{lhs_uid}})-[r:{rel_type}]-(r:{rhs_label}:{{rhs_uid_key}:{rhs_uid}})"
            "DELETE (r);",
            lhs_label=lhs_node.get_node_label(),
            lhs_uid_key=lhs_node.get_uid_key(),
            lhs_uid=lhs_node.get_uid(),
            rhs_label=rhs_node.get_node_label(),
            rhs_uid_key=rhs_node.get_uid_key(),
            rhs_uid=rhs_node.get_uid(),
            rel_type=cls.get_rel_type()
        )

    @classmethod
    def get_rel_props(cls, lhs_node, rhs_node):
        tx = Neo4j.get_db()
        results = tx.run(
            "MATCH (l:{lhs_label}:{{lhs_uid_key}:{lhs_uid}})-[r:{rel_type}]-(r:{rhs_label}:{{rhs_uid_key}:{rhs_uid}})"
            "RETURN r;",
            lhs_label=lhs_node.get_node_label(),
            lhs_uid_key=lhs_node.get_uid_key(),
            lhs_uid=lhs_node.get_uid(),
            rhs_label=rhs_node.get_node_label(),
            rhs_uid_key=rhs_node.get_uid_key(),
            rhs_uid=rhs_node.get_uid(),
            rel_type=cls.get_rel_type()
        )
        result = results.single()

        if result is None:
            raise LookupError("Relationship does not exist")

        # instantiate schema belonging to subclass
        schema = cls._SCHEMA()

        # map node data to dict using schema; fail when violates
        d = schema.load(result['r'])

        # return instance of populated subclass
        return cls(d)

    @classmethod
    def get_rel_type(cls):
        return str(cls.__name__)
