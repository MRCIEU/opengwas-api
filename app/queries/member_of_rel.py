from schemas.member_of_rel_schema import MemberOfRelSchema
from queries.unique_rel import UniqueRel


class MemberOfRel(UniqueRel):
    _TYPE = "MEMBER_OF"
    _SCHEMA = MemberOfRelSchema
