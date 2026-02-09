from decimal import Decimal, getcontext
from typing import Literal, Iterable
from sqlalchemy import or_, and_, between, union_all, select, case, asc, literal

from queries.models.dbsnp import DBSNP
from queries.models.phewas import PheWAS
from queries.models.proxies import get_proxies_model
from queries.models.tophits import get_tophits_model
from resources.globals import Globals


class MySQLQueries:
    dbsnp_build = 157
    non_numeric_chr = {'X': 23, 'Y': 24, 'MT': 25}

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

    @staticmethod
    def _encode_chr(chr_str):
        return {'X': 23, 'Y': 24, 'MT': 25}.get(chr_str, int(chr_str))

    @staticmethod
    def _decode_chr(chr_id):
        return str(chr_id) if chr_id <= 23 else {23: 'X', 24: 'Y', 25: 'MT'}[chr_id]

    @staticmethod
    def _lstrip_rsids(rsids: list[str]) -> list[str]:
        return [r[2:] for r in rsids]

    @staticmethod
    def _prepend_rsids(rows: Iterable, columns: list[str]) -> list[dict]:
        result = []
        for row in rows:
            r = dict(row)
            for col in columns:
                if r.get(col) is not None:
                    r[col] = f"rs{row[col]}"
            result.append(r)
        return result

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

    def get_snps_by_rsid(self, rsid_list: list[str]):
        query = select(*DBSNP.__table__.c).where(DBSNP.rsid.in_(self._lstrip_rsids(rsid_list)))
        # print(query.compile(compile_kwargs={"literal_binds": True}))

        result = Globals.mysql.session.execute(query).mappings().all()
        return self._prepend_rsids(result, ['rsid'])

    def get_snps_by_chrpos(self, chrpos_by_chr_id: dict):
        queries = []
        for chr_id, chrpos_list in chrpos_by_chr_id.items():
            conditions = []
            for cp in chrpos_list:
                if isinstance(cp, tuple):  # cprange
                    conditions.append(between(DBSNP.pos, cp[0], cp[1]))
                else:
                    conditions.append(DBSNP.pos == cp)
            queries.append(select(DBSNP).where(
                and_(
                    DBSNP.chr_id == chr_id,
                    or_(*conditions),
                ))
            )

        full_query = union_all(*queries)
        # print(full_query.compile(compile_kwargs={"literal_binds": True}))

        result = Globals.mysql.session.execute(full_query).mappings().all()
        return self._prepend_rsids(result, ['rsid'])

    def get_proxies(self, table_name: str, target_snps: list[str], r2: float, palindromic: Literal[0, 1], maf_threshold: float):
        target_snps = self._lstrip_rsids(target_snps)
        Proxies = get_proxies_model(table_name)
        if palindromic == 0:
            query = select(*Proxies.__table__.c,
                           case(
                               (Proxies.rsid_a.in_(target_snps), 'a'),
                               (Proxies.rsid_b.in_(target_snps), 'b'),
                           ).label('target_column')).where(
                and_(
                    or_(
                        Proxies.rsid_a.in_(target_snps),
                        Proxies.rsid_b.in_(target_snps),
                    ),
                    Proxies.r2 >= r2,
                    Proxies.palindromic == 0,
                )
            ).order_by(asc(Proxies.distance))
        else:
            query_a = select(*Proxies.__table__.c, literal('a').label('target_column')).where(
                and_(
                    Proxies.rsid_a.in_(target_snps),
                    Proxies.r2 >= r2,
                    or_(
                        Proxies.palindromic == 0,
                        and_(
                            Proxies.palindromic == 1,
                            Proxies.maf_a < maf_threshold,
                        ),
                    ),
                )
            )
            query_b = select(*Proxies.__table__.c, literal('b').label('target_column')).where(
                and_(
                    Proxies.rsid_b.in_(target_snps),
                    Proxies.r2 >= r2,
                    or_(
                        Proxies.palindromic == 0,
                        and_(
                            Proxies.palindromic == 1,
                            Proxies.maf_b < maf_threshold
                        ),
                    ),
                )
            )
            query = union_all(query_a, query_b).order_by(asc(Proxies.distance))

        # print(query.compile(compile_kwargs={"literal_binds": True}))

        result = Globals.mysql.session.execute(query).mappings().all()
        return self._prepend_rsids(result, ['rsid_a', 'rsid_b'])
