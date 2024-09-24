from flask import g
from flask_restx import Resource, reqparse, abort, Namespace
import time

from queries.es import *
from queries.redis_queries import RedisQueries
from queries.variants import *
from middleware.auth import jwt_required
from middleware.limiter import limiter, get_allowance_by_user_source, get_key_func_uid
from middleware.logger import logger as logger_middleware

api = Namespace('phewas', description="Perform PheWAS of specified variants across all available GWAS datasets")


def _get_cost(variants, fast=False):
    if len(variants) == 0:
        return 1
    variants = organise_variants(variants)
    return len(variants) * 20 if fast else (len(variants['rsid']) + len(variants['chrpos'])) * 75 + len(variants['cprange']) * 750


def _get_response_cost(result):
    return len(result)


@api.route('/<variant>/<pval>')
@api.hide
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

        start_time = time.time()

        try:
            result = run_phewas(user_email=g.user['uid'], variants=variants, pval=float(pval), index_list=[])
        except Exception as e:
            logger.error("Could not query summary stats: {}".format(e))
            abort(503)

        logger_middleware.log(g.user['uuid'], 'phewas_get', start_time, {'variant': len(variants)},
                              len(result), list(set([r['id'] for r in result])), len(set([r['rsid'] for r in result])))
        return result


@api.route('/slow')
@api.deprecated
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

        start_time = time.time()

        try:
            result = run_phewas(user_email=g.user['uid'], variants=args['variant'], pval=args['pval'], index_list=args['index_list'])
        except Exception as e:
            logger.error("Could not query summary stats: {}".format(e))
            abort(503)

        logger_middleware.log(g.user['uuid'], 'phewas_post', start_time, {'variant': len(args['variant'])},
                              len(result), list(set([r['id'] for r in result])), len(set([r['rsid'] for r in result])))
        return result


@api.route('')
@api.doc(
    description="Perform PheWAS of specified variants across all available GWAS datasets. This endpoint is faster, also accepts rsid, chrpos and cprange, but only accepts p < 0.01"
)
class PhewasFastPost(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('variant', required=False, type=str, action='append', default=[], help="List of rs IDs, chr:pos or chr:pos range  (hg19/b37). e.g rs1205,7:105561135,7:105561135-105563135")
    parser.add_argument('pval', type=float, required=False, default=0.01, help='P-value threshold (must < 0.01)')
    parser.add_argument('index_list', required=False, type=str, action='append', default=[], help="List of study indexes. If empty then searches across all indexes.")

    @api.expect(parser)
    @api.doc(id='phewas_fast_post')
    @jwt_required
    def post(self):
        args = self.parser.parse_args()
        if args['pval'] > 0.01:
            abort(400)

        with limiter.shared_limit(limit_value=get_allowance_by_user_source, scope='allowance_by_user_source', key_func=get_key_func_uid, cost=_get_cost(args['variant'], fast=True)):
            pass

        start_time = time.time()

        try:
            # result, timestamps = run_phewas_fast(user_email=g.user['uid'], variants=args['variant'], pval=args['pval'], index_list=args['index_list'])
            result = run_phewas_fast(user_email=g.user['uid'], variants=args['variant'], pval=args['pval'], index_list=args['index_list'])
        except Exception as e:
            logger.error("Could not query summary stats: {}".format(e))
            abort(503)

        with limiter.shared_limit(limit_value=get_allowance_by_user_source, scope='allowance_by_user_source', key_func=get_key_func_uid, cost=_get_response_cost(args['variant'])):
            pass

        logger_middleware.log(g.user['uuid'], 'phewas_fast_post', start_time, {'variant': len(args['variant'])},
                              len(result), list(set([r['id'] for r in result])), len(set([r['rsid'] for r in result])))
        # return result, 200, {'X-PROCESSING-TIME': ','.join([str(t) for t in timestamps])}
        return result


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

    return allres


def run_phewas_fast(user_email, variants, pval, index_list=None):
    variants = organise_variants(variants)

    rsid = variants['rsid']
    chrpos = variants['chrpos']
    cprange = variants['cprange']

    chr_pos = set()
    cpalleles = set()
    doc_ids_by_index = set()
    result = []
    # timestamps = [time.time()]

    try:
        if len(rsid) > 0:
            total, hits = snps(rsid)
            for doc in hits:
                chr_pos.add((doc['_source']['CHROM'], doc['_source']['POS'], doc['_source']['POS']))
        if len(chrpos) > 0:
            for cp in chrpos:
                chr_pos.add((str(cp['chr']), cp['start'], cp['end']))
        if len(cprange) > 0:
            for cpr in cprange:
                chr_pos.add((str(cpr['chr']), cpr['start'], cpr['end']))
        # timestamps.append(time.time())
        cpalleles = RedisQueries('phewas_cpalleles', provider='ieu-ssd-proxy').get_cpalleles_of_chr_pos(chr_pos)
        # timestamps.append(time.time())
    except Exception as e:
        logging.error("Could not obtain cpalleles from fast index (first tier): {}".format(e))
        flask.abort(503, e)

    try:
        doc_ids_by_index = RedisQueries('phewas_docids', provider='ieu-ssd-proxy').get_doc_ids_of_cpalleles_and_pval(cpalleles, pval)
        # timestamps.append(time.time())
    except Exception as e:
        logging.error("Could not obtain doc IDs from fast index (second tier): {}".format(e))
        flask.abort(503, e)

    try:
        result = elastic_query_phewas_by_doc_ids(doc_ids_by_index, user_email=user_email, index_list=index_list)
        # timestamps.append(time.time())
    except Exception as e:
        logging.error("Could not obtain docs from database: {}".format(e))
        flask.abort(503, e)

    # for i in [4, 3, 2, 1]:
    #     timestamps[i] = round((timestamps[i] - timestamps[i - 1]) * 1000)
    # timestamps.pop(0)

    # return result, timestamps
    return result
