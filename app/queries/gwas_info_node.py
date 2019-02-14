from queries.unique_node import UniqueNode
from schemas.gwas_info_node_schema import GwasInfoNodeSchema
from resources._neo4j import Neo4j


class GwasInfo(UniqueNode):
    _UID_KEY = 'id'
    _SCHEMA = GwasInfoNodeSchema

    # TODO returns None
    @classmethod
    def get_next_numeric_id(cls):
        tx = Neo4j.get_db()
        results = tx.run(
            "MATCH (n:" + cls.get_node_label() + ") WHERE n." + cls._UID_KEY + " =~ 'bgc-*' RETURN max(toInteger(substring(n." + cls._UID_KEY + ", 4))) + 1 as uid;"
        )
        return results.single()['uid']
