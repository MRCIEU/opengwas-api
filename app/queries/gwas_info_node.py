from queries.unique_node import UniqueNode
from schemas.gwas_info_node_schema import GwasInfoNodeSchema


class GwasInfo(UniqueNode):
    _UID_KEY = 'id'
    _SCHEMA = GwasInfoNodeSchema
