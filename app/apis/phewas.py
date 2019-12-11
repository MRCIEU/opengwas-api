from flask_restplus import Resource, reqparse, abort, Namespace
from queries.es import *
from resources.auth import get_user_email
from flask import request
from resources.globals import Globals

api = Namespace('phewas', description="Perform PheWAS of specified variants across all available GWAS datasets")

parser1 = api.parser()
parser1.add_argument(
    'X-Api-Token', location='headers', required=False, default='null',
    help=Globals.AUTHTEXT)


@api.route('/<variant>/<pval>')
@api.expect(parser1)
@api.doc(
    description="Perform PheWAS of specified variants across all available GWAS datasets",
    params={
        'rsid': 'Comma-separated list of rs IDs to query from the GWAS IDs',
        'pval': 'P-value threshold. Default = 1e-3'
    }
)
class PhewasGet(Resource):
    def get(self, variant=None, pval=1e-3):
        if variant is None:
            abort(404)
        try:
            user_email = get_user_email(request.headers.get('X-Api-Token'))
            out = elastic_query_phewas(
                variant.split(','),
                pval,
                user_email
            )
            logger.debug('Size after filtering: '+str(len(outFilter)))
        except Exception as e:
            logger.error("Could not query summary stats: {}".format(e))
            abort(503)
        return out


parser2 = reqparse.RequestParser()
parser2.add_argument('variant', required=False, type=str, action='append', default=[], help="List of rs IDs")
parser2.add_argument('pval', type=float, required=False, default=1e-05, help='P-value threshold')
parser2.add_argument(
    'X-Api-Token', location='headers', required=False, default='null',
    help=Globals.AUTHTEXT)


@api.route('')
@api.doc(
    description="Perform PheWAS of specified variants across all available GWAS datasets."
)
class PhewasPost(Resource):
    @api.expect(parser2)
    def post(self):
        args = parser2.parse_args()
        try:
            user_email = get_user_email(request.headers.get('X-Api-Token'))
            out = elastic_query_phewas(
                args['variant'],
                args['pval'],
                user_email
            )
            logger.debug('Size after filtering: '+str(len(out)))
        except Exception as e:
            logger.error("Could not query summary stats: {}".format(e))
            abort(503)
        return out
