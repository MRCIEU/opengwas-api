from flask import request, g
from flask_restx import Resource, reqparse, abort, Namespace

from queries.es import *
from middleware.auth import jwt_required
from middleware.limiter import limiter, get_allowance_by_user_source, get_key_func_uid

api = Namespace('phewas', description="Perform PheWAS of specified variants across all available GWAS datasets")


def _get_cost(variants):
    if len(variants) == 0:
        return 1
    variants = organise_variants(variants)
    return (len(variants['rsid']) + len(variants['chrpos'])) * 75 + len(variants['cprange']) * 750


@api.route('/<variant>/<pval>')
@api.doc(
    description="Perform PheWAS of specified variants across all available GWAS datasets",
    params={
        'variant': "Comma-separated list of rs IDs, chr:pos or chr:pos range  (hg19/b37). e.g rs1205,7:105561135,7:105561135-105563135",
        'pval': "P-value threshold. Default = 1e-3"
    }
)
class PhewasGet(Resource):
    parser = api.parser()

    @api.expect(parser)
    @api.doc(id='phewas_get')
    @jwt_required
    def get(self, variant='', pval=1e-3):
        variants = variant.split(',')

        with limiter.shared_limit(limit_value=get_allowance_by_user_source, scope='allowance_by_user_source', key_func=get_key_func_uid, cost=_get_cost(variants)):
            pass

        if variants == ['']:
            abort(400)

        try:
            return run_phewas(user_email=g.user['uid'], variants=variants, pval=float(pval), index_list=[])
        except Exception as e:
            logger.error("Could not query summary stats: {}".format(e))
            abort(503)


@api.route('')
@api.doc(
    description="Perform PheWAS of specified variants across all available GWAS datasets."
)
class PhewasPost(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('variant', required=False, type=str, action='append', default=[], help="List of rs IDs, chr:pos or chr:pos range  (hg19/b37). e.g rs1205,7:105561135,7:105561135-105563135")
    parser.add_argument('pval', type=float, required=False, default=1e-05, help='P-value threshold')
    parser.add_argument('index_list', required=False, type=str, action='append', default=[], help="List of study indexes. If empty then searches across all indexes.")

    @api.expect(parser)
    @api.doc(id='phewas_post')
    @jwt_required
    def post(self):
        args = self.parser.parse_args()

        with limiter.shared_limit(limit_value=get_allowance_by_user_source, scope='allowance_by_user_source', key_func=get_key_func_uid, cost=_get_cost(args['variant'])):
            pass

        try:
            return run_phewas(user_email=g.user['uid'], variants=args['variant'], pval=args['pval'], index_list=args['index_list'])
        except Exception as e:
            logger.error("Could not query summary stats: {}".format(e))
            abort(503)


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
