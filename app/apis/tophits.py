from flask import g
from flask_restx import Resource, reqparse, abort, Namespace
import logging
import time

from queries.es import *
from resources.ld import *
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
            result = extract_instruments(g.user['uid'], args['id'], args['preclumped'], args['clump'], args['bychr'], args['pval'], args['r2'], args['kb'], args['pop'])
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
