from schemas.added_by_rel_schema import AddedByRelSchema
from queries.unique_rel import UniqueRel


class AddedByRel(UniqueRel):
    _SCHEMA = AddedByRelSchema
