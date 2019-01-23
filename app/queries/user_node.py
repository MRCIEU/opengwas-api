from queries.unique_node import UniqueNode


class User(UniqueNode):
    _UID_KEY = 'uid'
    _SCHEMA_CLASS_NAME = 'UserNodeSchema'
    _SCHEMA_MODULE_NAME = 'schemas.user_node_schema'
