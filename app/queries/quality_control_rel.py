from schemas.quality_control_rel_schema import QualityControlRelSchema
from queries.unique_rel import UniqueRel


class QualityControlRel(UniqueRel):
    _TYPE = "DID_QC"
    _SCHEMA = QualityControlRelSchema
