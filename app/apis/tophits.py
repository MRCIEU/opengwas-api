from collections import defaultdict
import json
import math
import time

from flask import g
from flask_restx import Resource, reqparse, abort, Namespace
from opentelemetry.trace import SpanKind, Status, StatusCode

from queries.cql_queries import get_permitted_studies
from queries.mysql_queries import MySQLQueries
from resources.ld import plink_clumping_rs
from resources.globals import Globals
from middleware.auth import jwt_required
from middleware.limiter import limiter, get_allowance_by_user_tier, get_key_func_uid
from middleware.logger import logger as logger_middleware


api = Namespace('tophits', description="Extract top hits based on p-value threshold from a GWAS dataset")


def _get_cost(ids, preclumped, clump):
    if len(ids) == 0:
        return 1
    # https://github.com/MRCIEU/ieugwasr/blob/HEAD/R/query.R
    # If clump = 1 and all thresholds (r2, kb and pval) are still in default value
    # Then preclumped = 1, use preclumped data (easy)
    if preclumped:
        return len(ids)
    # Else if clump = 0
    # Then just return all records (medium)
    if not clump:
        return len(ids) * 10
    # Else if clump = 1 and any threshold is different from default value
    # Then get all records and clump again (hard)
    return len(ids) * 30


@api.route('')
@api.doc(
    description="Extract top hits based on p-value threshold from a GWAS dataset.")
class Tophits(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('id', type=str, required=True, action='append',
                        help="list of GWAS study IDs")
    parser.add_argument('pval', type=float, required=False, default=0.00000005,
                        help="P-value threshold (must <= 0.01) (exponents not supported through Swagger)")
    parser.add_argument('preclumped', type=int, required=False, default=1,
                        help='Whether to use pre-clumped tophits (1) or not (0)')
    parser.add_argument('clump', type=int, required=False, default=1,
                        help='Whether to clump (1) or not (0)')
    parser.add_argument('r2', type=float, required=False, default=0.001,
                        help='Clumping parameter')
    parser.add_argument('kb', type=int, required=False, default=5000,
                        help='Clumping parameter')
    parser.add_argument('pop', type=str, required=False, default="EUR", choices=Globals.LD_POPULATIONS)

    @api.expect(parser)
    @api.doc(id='tophits_post')
    @jwt_required
    def post(self):
        args = self.parser.parse_args()

        with limiter.shared_limit(limit_value=get_allowance_by_user_tier, scope='allowance_by_user_tier',
                                  key_func=get_key_func_uid,
                                  cost=_get_cost(args['id'], args['preclumped'], args['clump'])):
            pass

        time_start = time.time()

        with Globals.tracer.start_as_current_span("tophits", kind=SpanKind.SERVER) as span:
            span.set_attribute('uuid', g.user['uuid'])

            # Check arguments
            with Globals.tracer.start_as_current_span("tophits.check_args", kind=SpanKind.SERVER) as span:
                if len(args['id']) == 0:
                    span.set_status(Status(StatusCode.ERROR, "EMPTY_ID_LIST"))
                    return {
                        "message": "Please provide at least one id.",
                    }, 400
                if args['pval'] is None:
                    args['pval'] = 0.00000005
                if not 0 < args['pval'] <= 0.01:
                    span.set_status(Status(StatusCode.ERROR, "INVALID_PVAL"))
                    return {
                        "message": "Please make sure 0 < pval <= 0.01.",
                    }, 400

            # Check access
            with Globals.tracer.start_as_current_span("tophits.check_access", kind=SpanKind.SERVER) as span:
                gwasinfo_permitted = get_permitted_studies(g.user['uid'], args['id'])
                gwas_ids_permitted = list(gwasinfo_permitted.keys())
                if len(gwas_ids_permitted) == 0:
                    return []

            # Query tophits
            with Globals.tracer.start_as_current_span("tophits.query", kind=SpanKind.SERVER) as span:
                try:
                    result, time_ms = extract_instruments(gwasinfo_permitted, args['preclumped'], args['clump'], args['pval'], args['r2'], args['kb'], args['pop'])
                except Exception as e:
                    span.set_attributes({
                        'args': json.dumps(args),
                    })
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, "UNABLE_TO_RETRIEVE_TOPHITS"))
                    return {
                        "message": "Unable to retrieve tophits (instruments).",
                        "trace_id": format(span.get_span_context().trace_id, '016x'),
                    }, 503

                span.set_attributes({
                    'n_result': len(result)
                })
                Globals.meters['histogram_time_per_gwas_id'].record(round(time_ms / len(gwas_ids_permitted)))

        logger_middleware.log(g.user['uuid'], 'tophits_post', time_start,
                              {'id': len(args['id']), 'preclumped': args['preclumped'], 'clump': args['clump']},
                              len(result), list(set([r['id'] for r in result])))
        return result


def extract_instruments(gwasinfo: dict, preclumped, clump, pval, r2, kb, pop="EUR"):
    mysql_queries = MySQLQueries()

    gwas_ids_by_node_ids_permitted = {node_id: gwas_id for node_id, gwas_id in Globals.all_ids.items() if gwas_id in gwasinfo.keys()}

    time_mysql_start = time.time()
    if preclumped:
        result_using_gwas_node_ids = mysql_queries.get_tophits('tophits_5e-8_10000_0.001', list(gwas_ids_by_node_ids_permitted.keys()), -math.log10(pval))
    else:
        result_using_gwas_node_ids = mysql_queries.get_tophits_from_phewas_by_gwas_id_n(list(gwas_ids_by_node_ids_permitted.keys()), -math.log10(pval))
    time_mysql_end = time.time()

    result = []
    for r in result_using_gwas_node_ids:
        result.append({
            'id': gwas_ids_by_node_ids_permitted[r['gwas_id_n']],
            'trait': gwasinfo[gwas_ids_by_node_ids_permitted[r['gwas_id_n']]]['trait'],
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

    if not preclumped and clump:
        rsids_by_gwas_id = defaultdict(list)
        pvals_by_gwas_id = defaultdict(list)
        results_by_gwas_id = defaultdict(list)
        for r in result:
            rsids_by_gwas_id[r['id']].append(r['rsid'])
            pvals_by_gwas_id[r['id']].append(r['p'])
            results_by_gwas_id[r['id']].append(r)

        results_clumped = []
        for gwas_id in results_by_gwas_id.keys():
            rsids_clumped = plink_clumping_rs(Globals.TMP_FOLDER, rsids_by_gwas_id[gwas_id], pvals_by_gwas_id[gwas_id], pval, pval, r2, kb, pop=pop)
            results_clumped += [x for x in results_by_gwas_id[gwas_id] if x['rsid'] in rsids_clumped]
        result = results_clumped

    result = sorted(result, key=lambda a: (a['id'], a['p']))
    return result, (time_mysql_end - time_mysql_start) * 1000
