from flask_restx import Resource, reqparse, abort, Namespace
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
        'variant': 'Comma-separated list of rs IDs, chr:pos or chr:pos range  (hg19/b37). e.g rs1205,7:105561135,7:105561135-105563135',
        'pval': 'P-value threshold. Default = 1e-3'
    }
)
class PhewasGet(Resource):
    @api.doc(id='get_phewas')
    def get(self, variant=None, pval=1e-3):
        if variant is None:
            abort(404)
        try:
            user_email = get_user_email(request.headers.get('X-Api-Token'))
            out = run_phewas(user_email=user_email, variants=variant.split(','), pval=float(pval), index_list=[])
        except Exception as e:
            logger.error("Could not query summary stats: {}".format(e))
            abort(503)
        return out


parser2 = reqparse.RequestParser()
parser2.add_argument('variant', required=False, type=str, action='append', default=[], help="List of rs IDs, chr:pos or chr:pos range  (hg19/b37). e.g rs1205,7:105561135,7:105561135-105563135")
parser2.add_argument('pval', type=float, required=False, default=1e-05, help='P-value threshold')
parser2.add_argument('index_list', required=False, type=str, action='append', default=[], help="List of study indexes. If empty then searches across all indexes.")
parser2.add_argument(
    'X-Api-Token', location='headers', required=False, default='null',
    help=Globals.AUTHTEXT)


@api.route('')
@api.doc(
    description="Perform PheWAS of specified variants across all available GWAS datasets."
)
class PhewasPost(Resource):
    @api.expect(parser2)
    @api.doc(id='post_phewas')
    def post(self):
        args = parser2.parse_args()
        try:
            user_email = get_user_email(request.headers.get('X-Api-Token'))
            out = run_phewas(user_email=user_email, variants=args['variant'], pval=args['pval'], index_list=args['index_list'])
        except Exception as e:
            logger.error("Could not query summary stats: {}".format(e))
            abort(503)
        return out


def run_phewas(user_email, variants, pval, index_list=None):
    variants = organise_variants(variants)

    rsid = variants['rsid']
    chrpos = variants['chrpos']
    cprange = variants['cprange']

    allres = []
    if len(rsid) > 0:
        try:
            res = elastic_query_phewas_rsid(rsid=rsid, user_email=user_email, pval=pval, index_list=index_list)
            allres += res
        except Exception as e:
            logging.error("Could not obtain summary stats: {}".format(e))
            flask.abort(503, e)

    if len(chrpos) > 0:
        try:
            res = elastic_query_phewas_chrpos(chrpos=chrpos, user_email=user_email, pval=pval, index_list=index_list)
            allres += res
        except Exception as e:
            logging.error("Could not obtain summary stats: {}".format(e))
            flask.abort(503, e)

    if len(cprange) > 0:
        try:
            res = elastic_query_phewas_cprange(cprange=cprange, user_email=user_email, pval=pval, index_list=index_list)
            allres += res
        except Exception as e:
            logging.error("Could not obtain summary stats: {}".format(e))
            flask.abort(503, e)

    logger.debug('Size before filtering: '+str(len(allres)))
    #allres = [x for x in allres if x['p'] < float(pval)]
    logger.debug('Size after filtering: '+str(len(allres)))
    return allres
