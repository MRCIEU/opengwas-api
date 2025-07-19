from flask import g
from flask_restx import Resource, reqparse, abort, Namespace
from collections import defaultdict
import logging
import math
import time

from queries.cql_queries import get_permitted_studies
from queries.es import elastic_query_pval, add_trait_to_result
from queries.mysql_queries import MySQLQueries
from queries.redis_queries import RedisQueries
from resources.ld import plink_clumping_rs
from resources.globals import Globals
from middleware.auth import jwt_required
from middleware.limiter import limiter, get_allowance_by_user_tier, get_key_func_uid
from middleware.logger import logger as logger_middleware


logger = logging.getLogger('debug-log')

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
    parser.add_argument('id', required=False, type=str, action='append', default=[], help="list of GWAS study IDs")
    parser.add_argument('pval', type=float, required=False, default=0.00000005,
                         help='P-value threshold; exponents not supported through Swagger')
    parser.add_argument('preclumped', type=int, required=False, default=1, help='Whether to use pre-clumped tophits')
    parser.add_argument('clump', type=int, required=False, default=1, help='Whether to clump (1) or not (0)')
    parser.add_argument('bychr', type=int, required=False, default=1,
                         help='Whether to extract by chromosome (1) or all at once (0). There is a limit on query results so bychr might be required for some well-powered datasets')
    parser.add_argument('r2', type=float, required=False, default=0.001, help='Clumping parameter')
    parser.add_argument('kb', type=int, required=False, default=5000, help='Clumping parameter')
    parser.add_argument('pop', type=str, required=False, default="EUR", choices=Globals.LD_POPULATIONS)

    @api.expect(parser)
    @api.doc(id='tophits_post')
    @jwt_required
    def post(self):
        args = self.parser.parse_args()

        with limiter.shared_limit(limit_value=get_allowance_by_user_tier, scope='allowance_by_user_tier', key_func=get_key_func_uid, cost=_get_cost(args['id'], args['preclumped'], args['clump'])):
            pass

        if len(args['id']) == 0:
            abort(400)

        start_time = time.time()

        try:
            result = extract_instruments_fast(g.user['uid'], args['id'], args['preclumped'], args['clump'], args['bychr'], args['pval'], args['r2'], args['kb'], args['pop'])
        except Exception as e:
            logger.error("Could not obtain tophits: {}".format(e))
            abort(503)

        logger_middleware.log(g.user['uuid'], 'tophits_post', start_time,
                              {'id': len(args['id']), 'preclumped': args['preclumped'], 'clump': args['clump']},
                              len(result), list(set([r['id'] for r in result])))
        return result


def extract_instruments(user_email, id, preclumped, clump, bychr, pval, r2, kb, pop="EUR"):
    outcomes = ",".join(["'" + x + "'" for x in id])
    outcomes_clean = outcomes.replace("'", "")
    logger.debug('searching ' + outcomes_clean)
    study_data = get_permitted_studies(user_email, id)
    outcomes_access = list(study_data.keys())
    logger.debug(str(outcomes_access))
    if len(outcomes_access) == 0:
        logger.debug('No outcomes left after permissions check')
        return []

    res = elastic_query_pval(studies=outcomes_access, pval=pval, tophits=preclumped, bychr=bychr)
    for i in range(len(res)):
        res[i]['id'] = res[i]['id'].replace('tophits-', '')

    # Sometimes there are tophits that are not significant
    # This is because tophits are pre-selected based on rsid
    # rsids can be multi-allelic so one form of the variant might be significant
    # while the other is not
    res = [x for x in res if x['p'] < pval]

    if not preclumped and clump == 1 and len(res) > 0:
        found_outcomes = set([x.get('id') for x in res])
        res_clumped = []
        for outcome in found_outcomes:
            logger.debug("clumping results for " + str(outcome))
            rsid = [x.get('rsid') for x in res if x.get('id') == outcome]
            p = [x.get('p') for x in res if x.get('id') == outcome]
            out = plink_clumping_rs(Globals.TMP_FOLDER, rsid, p, pval, pval, r2, kb, pop=pop)
            res_clumped = res_clumped + [x for x in res if x.get('id') == outcome and x.get('rsid') in out]
        return res_clumped
    res = add_trait_to_result(res, study_data)
    return res


def extract_instruments_fast(user_email, id, preclumped, clump, bychr, pval, r2, kb, pop="EUR"):
    mysql_queries = MySQLQueries()

    outcomes = ",".join(["'" + x + "'" for x in id])
    outcomes_clean = outcomes.replace("'", "")
    logger.debug('searching ' + outcomes_clean)
    studies_permitted = get_permitted_studies(user_email, id)
    if len(studies_permitted.keys()) == 0:
        logger.debug('No outcomes left after permissions check')
        return []

    gwas_ids_by_node_ids_permitted = {node_id: gwas_id for node_id, gwas_id in Globals.all_ids.items() if gwas_id in studies_permitted.keys()}

    # if preclumped:
        # res = RedisQueries('tophits_5e-8_10000_0.001', provider='ieu-db-proxy').get_tophits_of_datasets_by_pval(outcomes_access, pval)

    if preclumped:
        results_using_gwas_node_ids = mysql_queries.get_tophits('tophits_5e-8_10000_0.001', list(gwas_ids_by_node_ids_permitted.keys()), -math.log10(pval))
    else:
        results_using_gwas_node_ids = mysql_queries.get_tophits_from_phewas_by_gwas_id_n(list(gwas_ids_by_node_ids_permitted.keys()), -math.log10(pval))

    results = []
    for r in results_using_gwas_node_ids:
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

    # if not preclumped and clump == 1 and len(results_using_gwas_node_ids) > 0:
    #     found_outcomes = set([x.get('id') for x in results_using_gwas_node_ids])
    #     res_clumped = []
    #     for outcome in found_outcomes:
    #         logger.debug("clumping results for " + str(outcome))
    #         rsid = [x.get('rsid') for x in results_using_gwas_node_ids if x.get('id') == outcome]
    #         p = [x.get('p') for x in results_using_gwas_node_ids if x.get('id') == outcome]
    #         out = plink_clumping_rs(Globals.TMP_FOLDER, rsid, p, pval, pval, r2, kb, pop=pop)
    #         res_clumped = res_clumped + [x for x in results_using_gwas_node_ids if x.get('id') == outcome and x.get('rsid') in out]
    #     return res_clumped

    if not preclumped and clump:
        rsids_by_gwas_id = defaultdict(list)
        pvals_by_gwas_id = defaultdict(list)
        results_by_gwas_id = defaultdict(list)
        for r in results:
            rsids_by_gwas_id[r['id']].append(r['rsid'])
            pvals_by_gwas_id[r['id']].append(r['p'])
            results_by_gwas_id[r['id']].append(r)

        results_clumped = []
        for gwas_id in results_by_gwas_id.keys():
            logger.debug("clumping results for " + str(gwas_id))
            rsids_clumped = plink_clumping_rs(Globals.TMP_FOLDER, rsids_by_gwas_id[gwas_id], pvals_by_gwas_id[gwas_id], pval, pval, r2, kb, pop=pop)
            results_clumped += [x for x in results_by_gwas_id[gwas_id] if x['rsid'] in rsids_clumped]
        results = results_clumped

    return sorted(results, key=lambda a: a['p'])
