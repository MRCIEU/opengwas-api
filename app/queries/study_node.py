from queries.unique_node import UniqueNode


class Study(UniqueNode):
    _UID_KEY = 'id'
    _SCHEMA_CLASS_NAME = 'StudyNodeSchema'
    _SCHEMA_MODULE_NAME = 'schemas.study_node_schema'
