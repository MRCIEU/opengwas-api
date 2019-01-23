from queries.unique_node import UniqueNode


class Group(UniqueNode):
    _UID_KEY = 'gid'
    _SCHEMA_CLASS_NAME = 'GroupNodeSchema'
    _SCHEMA_MODULE_NAME = 'schemas.group_node_schema'
