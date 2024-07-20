from queries.unique_node import UniqueNode
from schemas.org_node_schema import OrgNodeSchema
from resources.neo4j import Neo4j


class Org(UniqueNode):
    _UID_KEY = 'uuid'
    _SCHEMA = OrgNodeSchema

    def create_node(self):
        # map using schema; fail when violates
        schema = self._SCHEMA()
        d = schema.load(self)

        if d.get(self._UID_KEY) is None:
            raise KeyError("You must provide a value for the unique key.")

        tx = Neo4j.get_db()
        tx.run(
            "MERGE (n:" + self.get_node_label() + " {" + self._UID_KEY + ": $uid});",
            uid=self.get(self._UID_KEY)
        )

    @classmethod
    def set_properties_from_ms(cls, uuid, ms_id, ms_name, ms_domains):
        tx = Neo4j.get_db()
        tx.run(
            "MATCH (n:" + cls.get_node_label() + " {" + cls._UID_KEY + ": $uuid}) SET n.ms_id=$ms_id, n.ms_name=$ms_name, n.ms_domains=$ms_domains;",
            uuid=uuid, ms_id=ms_id, ms_name=ms_name, ms_domains=ms_domains
        )

    @classmethod
    def set_properties_from_github(cls, uuid, gh_name, gh_domains):
        tx = Neo4j.get_db()
        tx.run(
            "MATCH (n:" + cls.get_node_label() + " {" + cls._UID_KEY + ": $uuid}) SET n.gh_name=$gh_name, n.gh_domains=$gh_domains;",
            uuid=uuid, gh_name=gh_name, gh_domains=gh_domains
        )
