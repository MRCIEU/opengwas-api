from queries.unique_node import UniqueNode
from schemas.group_node_schema import GroupNodeSchema


class Group(UniqueNode):
    _UID_KEY = 'name'
    _SCHEMA = GroupNodeSchema
