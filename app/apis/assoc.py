from flask import request, g
from flask_restx import Resource, reqparse, abort, Namespace

from middleware.auth import jwt_required
from middleware.limiter import limiter, get_allowance_by_user_source, get_key_func_uid
from queries.es import *

api = Namespace('associations', description="Retrieve GWAS associations")


def _get_cost(ids=None, variants=None, proxies=None):  # Note: both inputs should be non-empty
    if ids is None:
        ids = request.values.getlist('id')
    if variants is None:
        variants = request.values.getlist('variant')
    if proxies is None:
        proxies = request.values.get('proxies', None)
    return max(len(ids), len(variants)) * (1 if not proxies else 5)


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
    @api.doc(id='get_variants_gwas')
    @jwt_required
    def get(self, id=None, variant=None):
        if id is None or variant is None:
            abort(400)
        ids = id.split(',')
        variants = variant.split(',')

        with limiter.shared_limit(limit_value=get_allowance_by_user_source, scope='allowance_by_user_source', key_func=get_key_func_uid,
                                  cost=lambda: _get_cost(ids, variants)):
            pass

        try:
            return get_assoc(g.user['uid'], variants, ids, 1, 0.8, 1, 1, 0.3)
        except Exception as e:
            logger.error("Could not obtain SNP association: {}".format(e))
            abort(503)


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
    @api.doc(id='post_variants_gwas')
    @jwt_required
    @limiter.shared_limit(limit_value=get_allowance_by_user_source, scope='allowance_by_user_source', key_func=get_key_func_uid,
                          cost=_get_cost)
    def post(self):
        args = self.parser.parse_args()
        if len(args['id']) == 0 or len(args['variant']) == 0:
            abort(400)

        try:
            return get_assoc(g.user['uid'], args['variant'], args['id'], args['proxies'], args['r2'], args['align_alleles'],
                            args['palindromes'], args['maf_threshold'])
        except Exception as e:
            logger.error("Could not obtain SNP association: {}".format(e))
            abort(503)
