from schemas.qc_result_rel_schema import QCResultRelSchema
from queries.unique_rel import UniqueRel


class QCResultRel(UniqueRel):
    _TYPE = "HAS_QC"
    _SCHEMA = QCResultRelSchema
