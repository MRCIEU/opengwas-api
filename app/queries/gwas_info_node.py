from queries.unique_node import UniqueNode
from schemas.gwas_info_node_schema import GwasInfoNodeSchema
from resources.neo4j import Neo4j


class GwasInfo(UniqueNode):
    _UID_KEY = 'id'
    _SCHEMA = GwasInfoNodeSchema

    @classmethod
    def get_next_numeric_id(cls):
        tx = Neo4j.get_db()
        results = tx.run(
            "MATCH (n:" + cls.get_node_label() + ") WHERE n." + cls._UID_KEY + " =~ 'bgc-[0-9]*' RETURN max(toInteger(substring(n." + cls._UID_KEY + ", 4))) + 1 as uid;"
        )
        result = results.single()

        if result['uid'] is None:
            return "bgc-1"
        else:
            return "bgc-" + str(result['uid'])
