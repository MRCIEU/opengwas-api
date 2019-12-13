from flask_restplus import Resource, reqparse, abort, Namespace
from queries.es import *
from resources.auth import get_user_email
from flask import request
from resources.globals import Globals

api = Namespace('associations', description="Retrieve GWAS associations")

parser1 = api.parser()
parser1.add_argument(
    'X-Api-Token', location='headers', required=False, default='null',
    help=Globals.AUTHTEXT)


@api.route('/<id>/<variant>')
@api.expect(parser1)
@api.doc(
    description="Get specific variant associations for specifc GWAS datasets",
    params={
        'id': 'An ID or comma-separated list of GWAS dataset IDs',
        'variant': 'Comma-separated list of rs IDs or chr:position to query from the GWAS IDs. hg19/build37 chr:position can be single position or a range e.g rs1205,10:44865737,7:105561135-105563135'
    }
)
class AssocGet(Resource):
    def get(self, id=None, variant=None):
        if variant is None:
            abort(404)
        if id is None:
            abort(404)
        try:
            user_email = get_user_email(request.headers.get('X-Api-Token'))
            out = get_assoc(user_email, variant.split(','), id.split(','), 1, 0.8, 1, 1, 0.3)
        except Exception as e:
            logger.error("Could not obtain SNP association: {}".format(e))
            abort(503)
        return out


parser2 = reqparse.RequestParser()
parser2.add_argument('variant', required=False, type=str, action='append', default=[], help="List of variants as rsid or chr:pos or chr:pos1-pos2 where positions are in hg19/b37 e.g. ['rs1205', '7:105561135', '7:105561135-105563135']")
parser2.add_argument('id', required=False, type=str, action='append', default=[], help="list of GWAS study IDs")
parser2.add_argument('proxies', type=int, required=False, default=0, help="Whether to look for proxies (1) or not (0). Note that proxies won't be looked for range queries")
parser2.add_argument('r2', type=float, required=False, default=0.8, help="Minimum LD r2 for a proxy")
parser2.add_argument('align_alleles', type=int, required=False, default=1, help="Whether to align alleles")
parser2.add_argument('palindromes', type=int, required=False, default=1, help="Whether to allow palindromic proxies")
parser2.add_argument('maf_threshold', type=float, required=False, default=0.3,
                     help="Maximum MAF allowed for a palindromic variant")
parser2.add_argument(
    'X-Api-Token', location='headers', required=False, default='null',
    help=Globals.AUTHTEXT)


@api.route('')
@api.doc(
    description="Get specific variant associations for specifc GWAS datasets"
)
class AssocPost(Resource):
    @api.expect(parser2)
    def post(self):
        args = parser2.parse_args()

        if (len(args['id']) == 0):
            abort(405)

        if (len(args['variant']) == 0):
            abort(405)

        try:
            user_email = get_user_email(request.headers.get('X-Api-Token'))
            out = get_assoc(user_email, args['variant'], args['id'], args['proxies'], args['r2'], args['align_alleles'],
                            args['palindromes'], args['maf_threshold'])
        except Exception as e:
            logger.error("Could not obtain SNP association: {}".format(e))
            abort(503)
        return out, 200
