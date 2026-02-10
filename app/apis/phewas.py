from collections import defaultdict
import json
import math
import time

from flask import g
from flask_restx import Resource, reqparse, abort, Namespace
from opentelemetry.trace import SpanKind, Status, StatusCode

from middleware.auth import jwt_required
from middleware.limiter import limiter, get_allowance_by_user_tier, get_key_func_uid
from middleware.logger import logger as logger_middleware
from queries.cql_queries import get_permitted_studies
from queries.es import organise_variants
from queries.mysql_queries import MySQLQueries
from resources.globals import Globals

api = Namespace('phewas', description="Perform PheWAS of specified variants across all available GWAS datasets")


def _get_cost(variants, fast=False):
    if len(variants) == 0:
        return 1
    variants = organise_variants(variants)
    return len(variants) * 20 if fast else (len(variants['rsid']) + len(variants['chrpos'])) * 75 + len(variants['cprange']) * 750


def _get_response_cost(result):
    return len(result)


@api.route('')
@api.doc(
    description="Perform PheWAS of specified variants across all available GWAS datasets. Only accepts p <= 0.01"
)
class Phewas(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('variant', type=str, required=True, action='append',
                        help="List of rs IDs, chr:pos or chr:pos range  (hg19/b37). e.g rs1205,7:105561135,7:105561135-105563135")
    parser.add_argument('pval', type=float, required=False, default=0.01,
                        help="P-value threshold (must <= 0.01) (exponents not supported through Swagger)")
    parser.add_argument('index_list', type=str, required=False, action='append', default=[],
                        help="List of study indexes. If empty then searches across all indexes.")

    @api.expect(parser)
    @api.doc(id='phewas_post')
    @jwt_required
    def post(self):
        args = self.parser.parse_args()

        with limiter.shared_limit(limit_value=get_allowance_by_user_tier, scope='allowance_by_user_tier', key_func=get_key_func_uid, cost=_get_cost(args['variant'], fast=True)):
            pass

        time_start = time.time()

        with Globals.tracer.start_as_current_span("phewas", kind=SpanKind.SERVER) as span:
            span.set_attribute('uuid', g.user['uuid'])

            # Check arguments
            with Globals.tracer.start_as_current_span("phewas.check_args", kind=SpanKind.SERVER) as span:
                if not 0 < args['pval'] <= 0.01:
                    span.set_status(Status(StatusCode.ERROR, "INVALID_PVAL"))
                    return {
                        "message": "Please make sure 0 < pval <= 0.01.",
                    }, 400

            # Query phewas
            with Globals.tracer.start_as_current_span("phewas.query", kind=SpanKind.SERVER) as span:
                try:
                    result, n_variants, time_ms = run_phewas(user_email=g.user['uid'], variants=args['variant'], pval=args['pval'], batch_list=args['index_list'])
                except Exception as e:
                    span.set_attributes({
                        'args': json.dumps(args),
                    })
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, "UNABLE_TO_RETRIEVE_PHEWAS"))
                    return {
                        "message": "Unable to retrieve PheWAS.",
                        "trace_id": format(span.get_span_context().trace_id, '016x'),
                    }, 503

                span.set_attributes({
                    'n_variants': n_variants,
                    'n_results': len(result),
                })
                if n_variants > 0:
                    Globals.meters['histogram_time_per_variant'].record(round(time_ms / n_variants))

            span.set_status(Status(StatusCode.OK))

        with limiter.shared_limit(limit_value=get_allowance_by_user_tier, scope='allowance_by_user_tier', key_func=get_key_func_uid, cost=_get_response_cost(args['variant'])):
            pass

        logger_middleware.log(g.user['uuid'], 'phewas_fast_post', time_start, {'variant': len(args['variant'])},
                              len(result), list(set([r['id'] for r in result])), len(set([r['rsid'] for r in result])))

        return result


def run_phewas(user_email, variants, pval, batch_list=None):
    mysql_queries = MySQLQueries()

    variants = organise_variants(variants)

    rsid = variants['rsid']
    chrpos = variants['chrpos']
    cprange = variants['cprange']

    chrpos_by_chr_id = defaultdict(set)

    if len(rsid) > 0:
        snps = mysql_queries.get_snps_by_rsid(rsid)
        for s in snps:
            chrpos_by_chr_id[int(s['chr_id'])].add(s['pos'])
    if len(chrpos) > 0:
        for cp in chrpos:
            chrpos_by_chr_id[int(mysql_queries._encode_chr(cp['chr']))].add(cp['start'])
    if len(cprange) > 0:
        for cpr in cprange:
            chrpos_by_chr_id[int(mysql_queries._encode_chr(cpr['chr']))].add((cpr['start'], cpr['end']))

    time_mysql_start = time.time()
    results_using_gwas_node_ids = mysql_queries.get_phewas_by_chrpos(dict(chrpos_by_chr_id), -math.log10(pval))
    time_mysql_end = time.time()

    gwas_ids_by_node_ids = {r['gwas_id_n']: Globals.all_ids[r['gwas_id_n']] for r in results_using_gwas_node_ids}
    if len(batch_list) > 0:
        gwas_ids_by_node_ids = {node_id: gwas_id for node_id, gwas_id in gwas_ids_by_node_ids.items() if '-'.join(gwas_id.split('-', 2)[:2]) in batch_list}

    # Check access
    with Globals.tracer.start_as_current_span("phewas.query_phewas.check_access", kind=SpanKind.SERVER) as span:
        gwasinfo_permitted = get_permitted_studies(user_email, list(gwas_ids_by_node_ids.values()))
        gwas_ids_permitted = list(gwasinfo_permitted.keys())
        if len(gwas_ids_permitted) == 0:
            return [], len(chrpos_by_chr_id), 0

    gwas_ids_by_node_ids_permitted = {node_id: gwas_id for node_id, gwas_id in gwas_ids_by_node_ids.items() if gwas_id in gwasinfo_permitted.keys()}

    result = []
    for r in results_using_gwas_node_ids:
        if r['gwas_id_n'] in gwas_ids_by_node_ids_permitted.keys():
            result.append({
                'id': gwas_ids_by_node_ids_permitted[r['gwas_id_n']],
                'trait': gwasinfo_permitted[gwas_ids_by_node_ids_permitted[r['gwas_id_n']]]['trait'],
                'chr': mysql_queries._decode_chr(r['chr_id']),
                'position': r['pos'],
                'rsid': r['snp_id'],
                'ea': r['ea'],
                'nea': r['nea'],
                'eaf': r['eaf'],
                'beta': r['beta'],
                'se': r['se'],
                'p': mysql_queries._convert_lp(r['lp']),
                'n': mysql_queries._convert_ss(r['ss']),
            })

    result = sorted(result, key=lambda a: (a['id'], a['p']))
    return result, len(chrpos_by_chr_id), (time_mysql_end - time_mysql_start) * 1000
