from schemas.member_of_org_rel_schema import MemberOfOrgRelSchema
from queries.unique_rel import UniqueRel


class MemberOfOrgRel(UniqueRel):
    _TYPE = "MEMBER_OF_ORG"
    _SCHEMA = MemberOfOrgRelSchema
