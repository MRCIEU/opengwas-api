from decimal import Decimal, getcontext
from sqlalchemy import or_, and_, between, union_all, select

from queries.models.phewas import PheWAS
from queries.models.tophits import get_tophits_model
from resources.globals import Globals


class MySQLQueries:
    non_numeric_chr = {'X': 23, 'Y': 24, 'MT': 25}
    non_numeric_chr_reverse = {23: 'X', 24: 'Y', 25: 'MT'}

    def __init__(self):
        getcontext().prec = 10

    @staticmethod
    def _convert_lp(lp):
        if lp == '':
            return lp
        return 0 if lp == 999999 else float('{:.6g}'.format(Decimal('10') ** -Decimal(lp)))

    @staticmethod
    def _convert_ss(size):
        if size == '':
            return size
        return float(size) if '.' in size else int(size)

    def get_phewas_by_chrpos(self, chrpos_by_chr_id: dict, lp: float):
        queries = []
        for chr_id, chrpos_list in chrpos_by_chr_id.items():
            conditions = []
            for cp in chrpos_list:
                if isinstance(cp, tuple):  # cprange
                    conditions.append(between(PheWAS.pos, cp[0], cp[1]))
                else:
                    conditions.append(PheWAS.pos == cp)
            queries.append(select(PheWAS).where(
                and_(
                    PheWAS.chr_id == chr_id,
                    or_(*conditions),
                    PheWAS.lp > lp
                ))
            )

        full_query = union_all(*queries)
        # print(full_query.compile(compile_kwargs={"literal_binds": True}))

        result = Globals.mysql.session.execute(full_query).mappings().all()
        return result

    def get_tophits_from_phewas_by_gwas_id_n(self, gwas_id_n_list: list[int], lp: float):
        query = select(*PheWAS.__table__.c).where(
            and_(
                PheWAS.gwas_id_n.in_(gwas_id_n_list),
                PheWAS.lp > lp
            )
        )
        # print(query.compile(compile_kwargs={"literal_binds": True}))

        result = Globals.mysql.session.execute(query).mappings().all()
        return result

    def get_tophits(self, table_name: str, gwas_id_n_list: list[int], lp: float):
        Tophits = get_tophits_model(table_name)
        query = select(*Tophits.__table__.c).where(
            and_(
                Tophits.gwas_id_n.in_(gwas_id_n_list),
                Tophits.lp > lp
            )
        )
        # print(query.compile(compile_kwargs={"literal_binds": True}))

        result = Globals.mysql.session.execute(query).mappings().all()
        return result
