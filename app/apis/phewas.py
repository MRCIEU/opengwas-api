from collections import defaultdict
from flask import g
from flask_restx import Resource, reqparse, abort, Namespace
import math
import time
import traceback

from middleware.auth import jwt_required
from middleware.limiter import limiter, get_allowance_by_user_tier, get_key_func_uid
from middleware.logger import logger as logger_middleware
from queries.assoc_queries_by_chunks import get_assoc_chunked
from queries.cql_queries import get_permitted_studies
from queries.es import elastic_query_phewas_rsid, elastic_query_phewas_chrpos, elastic_query_phewas_cprange, organise_variants
from queries.mysql_queries import MySQLQueries
from queries.variants import snps
from resources.globals import Globals

api = Namespace('phewas', description="Perform PheWAS of specified variants across all available GWAS datasets")


def _get_cost(variants, fast=False):
    if len(variants) == 0:
        return 1
    variants = organise_variants(variants)
    return len(variants) * 20 if fast else (len(variants['rsid']) + len(variants['chrpos'])) * 75 + len(variants['cprange']) * 750


def _get_response_cost(result):
    return len(result)


# @api.route('/<variant>/<pval>')
# @api.hide
# @api.doc(
#     description="Perform PheWAS of specified variants across all available GWAS datasets",
#     params={
#         'variant': "Comma-separated list of rs IDs, chr:pos or chr:pos range  (hg19/b37). e.g rs1205,7:105561135,7:105561135-105563135",
#         'pval': "P-value threshold. Default = 1e-3"
#     }
# )
# class PhewasGet(Resource):
#     parser = api.parser()
#
#     @api.expect(parser)
#     @api.doc(id='phewas_get')
#     @jwt_required
#     def get(self, variant='', pval=1e-3):
#         variants = variant.split(',')
#
#         with limiter.shared_limit(limit_value=get_allowance_by_user_tier, scope='allowance_by_user_tier', key_func=get_key_func_uid, cost=_get_cost(variants)):
#             pass
#
#         if variants == ['']:
#             abort(400)
#
#         start_time = time.time()
#
#         try:
#             result = run_phewas(user_email=g.user['uid'], variants=variants, pval=float(pval), index_list=[])
#         except Exception as e:
#             logger.error("Could not query summary stats: {}".format(e))
#             abort(503)
#
#         logger_middleware.log(g.user['uuid'], 'phewas_get', start_time, {'variant': len(variants)},
#                               len(result), list(set([r['id'] for r in result])), len(set([r['rsid'] for r in result])))
#         return result
#
#
# @api.route('/slow')
# @api.deprecated
# @api.doc(
#     description="Perform PheWAS of specified variants across all available GWAS datasets."
# )
# class PhewasPost(Resource):
#     parser = reqparse.RequestParser()
#     parser.add_argument('variant', required=False, type=str, action='append', default=[], help="List of rs IDs, chr:pos or chr:pos range  (hg19/b37). e.g rs1205,7:105561135,7:105561135-105563135")
#     parser.add_argument('pval', type=float, required=False, default=1e-05, help='P-value threshold')
#     parser.add_argument('index_list', required=False, type=str, action='append', default=[], help="List of study indexes. If empty then searches across all indexes.")
#
#     @api.expect(parser)
#     @api.doc(id='phewas_post')
#     @jwt_required
#     def post(self):
#         args = self.parser.parse_args()
#
#         with limiter.shared_limit(limit_value=get_allowance_by_user_tier, scope='allowance_by_user_tier', key_func=get_key_func_uid, cost=_get_cost(args['variant'])):
#             pass
#
#         start_time = time.time()
#
#         try:
#             result = run_phewas(user_email=g.user['uid'], variants=args['variant'], pval=args['pval'], index_list=args['index_list'])
#         except Exception as e:
#             logger.error("Could not query summary stats: {}".format(e))
#             abort(503)
#
#         logger_middleware.log(g.user['uuid'], 'phewas_post', start_time, {'variant': len(args['variant'])},
#                               len(result), list(set([r['id'] for r in result])), len(set([r['rsid'] for r in result])))
#         return result


@api.route('')
@api.doc(
    description="Perform PheWAS of specified variants across all available GWAS datasets. This endpoint is faster, also accepts rsid, chrpos and cprange, but only accepts p <= 0.01"
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
            abort(400, "pval must be no more than 0.01")

        with limiter.shared_limit(limit_value=get_allowance_by_user_tier, scope='allowance_by_user_tier', key_func=get_key_func_uid, cost=_get_cost(args['variant'], fast=True)):
            pass

        start_time = time.time()

        try:
            result, timestamps = run_phewas_fast(user_email=g.user['uid'], variants=args['variant'], pval=args['pval'], batch_list=args['index_list'])
            logger_middleware.log_info(g.user['uuid'], 'phewas_fast_mysql', {'n_tasks': len(result)}, [round((timestamps[i + 1] - timestamps[i]) * 1000, 2) for i in range(len(timestamps) - 1)])
        except Exception as e:
            # if "too many" in str(e):
            #     abort(400, str(e))
            log_timestamp = logger_middleware.log_error(g.user['uuid'], 'phewas_fast_post', args, traceback.format_exc())
            abort(503, f"Something went wrong. Please try again later. If the problem persists please let us know the error ID: {log_timestamp}")

        with limiter.shared_limit(limit_value=get_allowance_by_user_tier, scope='allowance_by_user_tier', key_func=get_key_func_uid, cost=_get_response_cost(args['variant'])):
            pass

        logger_middleware.log(g.user['uuid'], 'phewas_fast_post', start_time, {'variant': len(args['variant'])},
                              len(result), list(set([r['id'] for r in result])), len(set([r['rsid'] for r in result])))
        return result


# def run_phewas(user_email, variants, pval, index_list=None):
#     variants = organise_variants(variants)
#
#     rsid = variants['rsid']
#     chrpos = variants['chrpos']
#     cprange = variants['cprange']
#
#     allres = []
#     if len(rsid) > 0:
#         try:
#             res = elastic_query_phewas_rsid(rsid=rsid, user_email=user_email, pval=pval, index_list=index_list)
#             allres += res
#         except Exception as e:
#             logging.error("Could not obtain summary stats: {}".format(e))
#             flask.abort(503, e)
#
#     if len(chrpos) > 0:
#         try:
#             res = elastic_query_phewas_chrpos(chrpos=chrpos, user_email=user_email, pval=pval, index_list=index_list)
#             allres += res
#         except Exception as e:
#             logging.error("Could not obtain summary stats: {}".format(e))
#             flask.abort(503, e)
#
#     if len(cprange) > 0:
#         try:
#             res = elastic_query_phewas_cprange(cprange=cprange, user_email=user_email, pval=pval, index_list=index_list)
#             allres += res
#         except Exception as e:
#             logging.error("Could not obtain summary stats: {}".format(e))
#             flask.abort(503, e)
#
#     return allres


def run_phewas_fast(user_email, variants, pval, batch_list=None):
    mysql_queries = MySQLQueries()

    variants = organise_variants(variants)

    rsid = variants['rsid']
    chrpos = variants['chrpos']
    cprange = variants['cprange']

    chrpos_by_chr_id = defaultdict(set)
    timestamps = [time.time()]

    if len(rsid) > 0:
        total, hits = snps(rsid)
        for doc in hits:
            chrpos_by_chr_id[int(mysql_queries.non_numeric_chr.get(doc['_source']['CHR'], doc['_source']['CHR']))].add(doc['_source']['POS'])
    if len(chrpos) > 0:
        for cp in chrpos:
            chrpos_by_chr_id[int(mysql_queries.non_numeric_chr.get(cp['chr'], cp['chr']))].add(cp['start'])
    if len(cprange) > 0:
        for cpr in cprange:
            chrpos_by_chr_id[int(mysql_queries.non_numeric_chr.get(cpr['chr'], cpr['chr']))].add((cpr['start'], cpr['end']))
    timestamps.append(time.time())
    # cpalleles = RedisQueries('phewas_cpalleles', provider='ieu-ssd-proxy').get_cpalleles_of_chr_pos(chr_pos)
    # timestamps.append(time.time())

    # chrpos_by_gwas_node_ids = RedisQueries('phewas_gwas_n_ids', provider='ieu-ssd-proxy').get_gwas_n_ids_of_cpalleles_and_pval(cpalleles, pval)
    # timestamps.append(time.time())

    results_using_gwas_node_ids = mysql_queries.get_phewas_by_chrpos(dict(chrpos_by_chr_id), -math.log10(pval))
    timestamps.append(time.time())

    # result = elastic_query_phewas_by_doc_ids(doc_ids_by_index, user_email=user_email, batch_list=batch_list)
    # gwas_ids_by_node_ids = {gwas_node_id: Globals.all_ids[gwas_node_id] for gwas_node_id in chrpos_by_gwas_node_ids.keys()}
    gwas_ids_by_node_ids = {r['gwas_id_n']: Globals.all_ids[r['gwas_id_n']] for r in results_using_gwas_node_ids}
    if len(batch_list) > 0:
        gwas_ids_by_node_ids = {node_id: gwas_id for node_id, gwas_id in gwas_ids_by_node_ids.items() if '-'.join(gwas_id.split('-', 2)[:2]) in batch_list}
    studies_permitted = get_permitted_studies(user_email, list(gwas_ids_by_node_ids.values()))
    gwas_ids_by_node_ids_permitted = {node_id: gwas_id for node_id, gwas_id in gwas_ids_by_node_ids.items() if gwas_id in studies_permitted.keys()}

    results = []
    for r in results_using_gwas_node_ids:
        if r['gwas_id_n'] in gwas_ids_by_node_ids_permitted.keys():
            results.append({
                'id': gwas_ids_by_node_ids_permitted[r['gwas_id_n']],
                'trait': studies_permitted[gwas_ids_by_node_ids_permitted[r['gwas_id_n']]]['trait'],
                'chr': str(r['chr_id']) if r['chr_id'] <= 23 else mysql_queries.non_numeric_chr_reverse[r['chr_id']],
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
    timestamps.append(time.time())
    return sorted(results, key=lambda a: a['p']), timestamps

    # if len(gwas_ids_by_node_ids_permitted) > 96:
    #     raise Exception(f"There are {len(gwas_ids_by_node_ids_permitted)} associations found, which is too many. Please use a smaller pval and/or specify the list of batches so that the number of associations is no more than 96.")

    # results_all = []
    # n_chunks_accessed_all = 0
    # print(len(gwas_ids_by_node_ids_permitted))
    # i = 1
    # for gwas_node_id, gwas_id in gwas_ids_by_node_ids_permitted.items():
    #     results, n_chunks_accessed = get_assoc_chunked(user_email, chrpos_by_gwas_node_ids[gwas_node_id], [gwas_id],
    #                                                    proxies=0, study_data=permitted_studies)
    #     results_all += results
    #     n_chunks_accessed_all += n_chunks_accessed
    #     print(i)
    #     i += 1
    # timestamps.append(time.time())

    # for i in [4, 3, 2, 1]:
    #     timestamps[i] = round((timestamps[i] - timestamps[i - 1]) * 1000)
    # timestamps.pop(0)

    # return result, timestamps
    # return results_all
