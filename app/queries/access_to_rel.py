from schemas.access_to_rel_schema import AccessToRelSchema
from queries.unique_rel import UniqueRel


class AccessToRel(UniqueRel):
    _TYPE = "ACCESS_TO"
    _SCHEMA = AccessToRelSchema
