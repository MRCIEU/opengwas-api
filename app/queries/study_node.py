from queries.unique_node import UniqueNode
from schemas.study_node_schema import StudyNodeSchema


class Study(UniqueNode):
    _UID_KEY = 'id'
    _SCHEMA = StudyNodeSchema
