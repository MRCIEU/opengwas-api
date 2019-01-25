from queries.unique_node import UniqueNode
from schemas.user_node_schema import UserNodeSchema


class User(UniqueNode):
    _UID_KEY = 'uid'
    _SCHEMA = UserNodeSchema
