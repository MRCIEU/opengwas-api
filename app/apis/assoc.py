from flask import g
from flask_restx import Resource, reqparse, abort, Namespace
import math
import time
import traceback

from middleware.auth import jwt_required
from middleware.limiter import limiter, get_allowance_by_user_tier, get_key_func_uid
from middleware.logger import logger as logger_middleware
from queries.assoc_queries_by_chunks import get_assoc_chunked
from queries.es import *

api = Namespace('associations', description="Retrieve GWAS associations")


def _get_cost(ids=None, variants=None, proxies=0):  # Note: both inputs should be non-empty
    return max(len(ids), len(variants)) * (1 if proxies == 1 else 5)


def _compare_results(r0, r1):
    r0fset = {frozenset(a.items()) for a in r0}
    r1fset = {frozenset(a.items()) for a in r1}

    r0uniq = r0fset - r1fset
    r1uniq = r1fset - r0fset

    anomalies = []

    r0uniq = [{a[0]: a[1] for a in fset} for fset in r0uniq]
    r0uniq_dict = {f"{a['chr']}_{a['position']}_{a['rsid']}_{a['ea']}_{a['nea']}": a for a in r0uniq}
    if len(r0uniq_dict) != len(r0uniq):
        anomalies.append(['DUPLICATE_ID', 'r0'])

    r1uniq = [{a[0]: a[1] for a in fset} for fset in r1uniq]
    r1uniq_dict = {f"{a['chr']}_{a['position']}_{a['rsid']}_{a['ea']}_{a['nea']}": a for a in r1uniq}
    if len(r1uniq_dict) != len(r1uniq):
        anomalies.append(['DUPLICATE_ID', 'r1'])

    print(len(r0uniq_dict), len(r1uniq_dict))

    def _compare(dict1, dict2):
        for id in dict1.keys():
            if id not in dict2:
                anomalies.append(['MISSING_ID', id])
            elif dict1[id] != dict2[id]:
                diff_keys = {k for k in dict1[id] if dict1[id][k] != dict2[id][k]}
                if not (
                    (diff_keys == {'n'} and int(dict1[id]['n']) == int(dict2[id]['n'])) or
                    (diff_keys == {'beta', 'eaf'} and
                        math.isclose(float(dict1[id]['beta']) * -1, float(dict2[id]['beta']), rel_tol=1e-6) and
                        math.isclose(float(dict1[id]['eaf']) + float(dict2[id]['eaf']), 1.000000, rel_tol=1e-6)
                    )
                ):
                    anomalies.append(['DIFF_IN_VALUE', dict1[id], dict2[id], diff_keys])

    _compare(r0uniq_dict, r1uniq_dict)
    _compare(r1uniq_dict, r0uniq_dict)

    return anomalies


@api.route('/<id>/<variant>')
@api.doc(
    description="Get specific variant associations for specifc GWAS datasets",
    params={
        'id': 'An ID or comma-separated list of GWAS dataset IDs',
        'variant': 'Comma-separated list of rs IDs or chr:position to query from the GWAS IDs. hg19/build37 chr:position can be single position or a range e.g rs1205,10:44865737,7:105561135-105563135'
    }
)
class AssocGet(Resource):
    parser = api.parser()

    @api.expect(parser)
    @api.doc(id='assoc_get')
    @jwt_required
    def get(self, id='', variant=''):
        ids = id.split(',')  # ''.split(',') == ['']
        variants = variant.split(',')

        with limiter.shared_limit(limit_value=get_allowance_by_user_tier, scope='allowance_by_user_tier', key_func=get_key_func_uid, cost=_get_cost(ids, variants, proxies=1)):
            pass

        if ids == [''] or variants == ['']:
            abort(400)

        start_time = time.time()

        try:
            result = get_assoc(g.user['uid'], variants, ids, 1, 0.8, 1, 1, 0.3)
        except Exception as e:
            logger.error("Could not obtain SNP association: {}".format(e))
            abort(503)

        logger_middleware.log(g.user['uuid'], 'assoc_get', start_time,
                              {'id': len(ids), 'variant': len(variants), 'proxies': 1},
                              len(result), list(set([r['id'] for r in result])), len(set([r['rsid'] for r in result])))
        return result

@api.route('')
@api.doc(
    description="Get specific variant associations for specifc GWAS datasets"
)
class AssocPost(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('variant', required=False, type=str, action='append', default=[],
                         help="List of variants as rsid or chr:pos or chr:pos1-pos2 where positions are in hg19/b37 e.g. ['rs1205', '7:105561135', '7:105561135-105563135']")
    parser.add_argument('id', required=False, type=str, action='append', default=[], help="list of GWAS study IDs")
    parser.add_argument('proxies', type=int, required=False, default=0,
                         help="Whether to look for proxies (1) or not (0). Note that proxies won't be looked for range queries")
    parser.add_argument('r2', type=float, required=False, default=0.8, help="Minimum LD r2 for a proxy")
    parser.add_argument('align_alleles', type=int, required=False, default=1, help="Whether to align alleles")
    parser.add_argument('palindromes', type=int, required=False, default=1,
                         help="Whether to allow palindromic proxies")
    parser.add_argument('maf_threshold', type=float, required=False, default=0.3,
                         help="Maximum MAF allowed for a palindromic variant")

    @api.expect(parser)
    @api.doc(id='assoc_post')
    @jwt_required
    def post(self):
        args = self.parser.parse_args()

        with limiter.shared_limit(limit_value=get_allowance_by_user_tier, scope='allowance_by_user_tier', key_func=get_key_func_uid, cost=_get_cost(args['id'], args['variant'], args['proxies'])):
            pass

        if len(args['id']) == 0 or len(args['variant']) == 0:
            abort(400)

        start_time = time.time()

        try:
            result = get_assoc(g.user['uid'], args['variant'], args['id'], args['proxies'], args['r2'], args['align_alleles'], args['palindromes'], args['maf_threshold'])
        except Exception as e:
            logger.error("Could not obtain SNP association: {}".format(e))
            abort(503)

        logger_middleware.log(g.user['uuid'], 'assoc_post', start_time,
                              {'id': len(args['id']), 'variant': len(args['variant']), 'proxies': args['proxies']},
                              len(result), list(set([r['id'] for r in result])), len(set([r['rsid'] for r in result])))

        # return result

        start_time = time.time()

        try:
            result_from_chunks = get_assoc_chunked(g.user['uid'], args['variant'], args['id'], args['proxies'], args['r2'], args['align_alleles'], args['palindromes'], args['maf_threshold'])
        except Exception as e:
            logger.error("Could not obtain SNP association: {}".format(e))
            abort(503)

        logger_middleware.log(g.user['uuid'], 'assoc_chunked_post', start_time,
                              {'id': len(args['id']), 'variant': len(args['variant']), 'proxies': args['proxies']},
                              len(result_from_chunks), list(set([r['id'] for r in result_from_chunks])), len(set([r['rsid'] for r in result_from_chunks])))

        try:
            anomalies = _compare_results(result, result_from_chunks)
            assert anomalies == []
        except AssertionError as e:
            log_timestamp = logger_middleware.log_error(g.user['uuid'], 'assoc_post', args, anomalies)
        except Exception as e:
            log_timestamp = logger_middleware.log_error(g.user['uuid'], 'assoc_post', args, traceback.format_exc())
            return {
                'error_log_timestamp': log_timestamp
            }, 503

        return result


@api.route('/chunked')
@api.doc(
    description="Get specific variant associations for specifc GWAS datasets (Implementation of chunking backed by object storage - beta version)"
)
class AssocChunkedPost(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('variant', required=False, type=str, action='append', default=[],
                         help="List of variants as rsid or chr:pos or chr:pos1-pos2 where positions are in hg19/b37 e.g. ['rs1205', '7:105561135', '7:105561135-105563135']")
    parser.add_argument('id', required=False, type=str, action='append', default=[], help="list of GWAS study IDs")
    parser.add_argument('proxies', type=int, required=False, default=0,
                         help="Whether to look for proxies (1) or not (0). Note that proxies won't be looked for range queries")
    parser.add_argument('r2', type=float, required=False, default=0.8, help="Minimum LD r2 for a proxy")
    parser.add_argument('align_alleles', type=int, required=False, default=1, help="Whether to align alleles")
    parser.add_argument('palindromes', type=int, required=False, default=1,
                         help="Whether to allow palindromic proxies")
    parser.add_argument('maf_threshold', type=float, required=False, default=0.3,
                         help="Maximum MAF allowed for a palindromic variant")

    @api.expect(parser)
    @api.doc(id='assoc_chunked_post')
    @jwt_required
    def post(self):
        args = self.parser.parse_args()

        with limiter.shared_limit(limit_value=get_allowance_by_user_tier, scope='allowance_by_user_tier', key_func=get_key_func_uid, cost=_get_cost(args['id'], args['variant'], args['proxies'])):
            pass

        if len(args['id']) == 0 or len(args['variant']) == 0:
            abort(400)

        start_time = time.time()

        try:
            result = get_assoc_chunked(g.user['uid'], args['variant'], args['id'], args['proxies'], args['r2'], args['align_alleles'], args['palindromes'], args['maf_threshold'])
        except Exception as e:
            logger.error("Could not obtain SNP association: {}".format(e))
            abort(503)

        logger_middleware.log(g.user['uuid'], 'assoc_chunked_post', start_time,
                              {'id': len(args['id']), 'variant': len(args['variant']), 'proxies': args['proxies']},
                              len(result), list(set([r['id'] for r in result])), len(set([r['rsid'] for r in result])))
        return result
