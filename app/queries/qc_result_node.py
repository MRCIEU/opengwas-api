from queries.unique_node import UniqueNode
from schemas.qc_result_node_schema import QCResultNodeSchema


class QCResult(UniqueNode):
    _UID_KEY = 'id'
    _SCHEMA = QCResultNodeSchema
