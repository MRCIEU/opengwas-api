from flask_restplus import Resource, reqparse, abort, Namespace
from queries.es import *
from resources.ld import *
from resources.auth import get_user_email
from queries.cql_queries import get_all_gwas_ids_for_user
from flask import request
import logging

logger = logging.getLogger('debug-log')
api = Namespace('tophits', description="Extract top hits based on p-value threshold from a GWAS dataset")
parser1 = reqparse.RequestParser()
parser1.add_argument('id', required=False, type=str, action='append', default=[], help="list of GWAS study IDs")
parser1.add_argument('pval', type=float, required=False, default=0.00000005,
                     help='P-value threshold; exponents not supported through Swagger')
parser1.add_argument('preclumped', type=int, required=False, default=1, help='Whether to use pre-clumped tophits')
parser1.add_argument('clump', type=int, required=False, default=1, help='Whether to clump (1) or not (0)')
parser1.add_argument('r2', type=float, required=False, default=0.001, help='Clumping parameter')
parser1.add_argument('kb', type=int, required=False, default=5000, help='Clumping parameter')
parser1.add_argument(
    'X-Api-Token', location='headers', required=False, default='null',
    help='Public datasets can be queried without any authentication, but some studies are only accessible by specific users. To authenticate we use Google OAuth2.0 access tokens. The easiest way to obtain an access token is through the [ieugwasr](https://mrcieu.github.io/ieugwasr/articles/guide.html#authentication) package using the `get_access_token()` function.')


@api.route('')
@api.doc(
    description="Extract top hits based on p-value threshold from a GWAS dataset.")
class Tophits(Resource):
    @api.expect(parser1)
    def post(self):
        args = parser1.parse_args()
        user_email = get_user_email(request.headers.get('X-Api-Token'))
        try:
            out = extract_instruments(user_email, args['id'], args['preclumped'], args['clump'], args['pval'], args['r2'], args['kb'])
        except Exception as e:
            logger.error("Could not obtain tophits: {}".format(e))
            abort(503)
        return out


def extract_instruments(user_email, id, preclumped, clump, pval, r2, kb):
    outcomes = ",".join(["'" + x + "'" for x in id])
    outcomes_clean = outcomes.replace("'", "")
    logger.debug('searching ' + outcomes_clean)
    study_data = get_permitted_studies(user_email, id)
    outcomes_access = list(study_data.keys())
    logger.debug(str(outcomes_access))
    if len(outcomes_access) == 0:
        logger.debug('No outcomes left after permissions check')
        return json.dumps([], ensure_ascii=False)

    res = elastic_query_pval(studies=outcomes_access, pval=pval, tophits=preclumped)
    for i in range(len(res)):
        res[i]['id'] = res[i]['id'].replace('tophits-', '')

    if not preclumped and clump == 1 and len(res) > 0:
        found_outcomes = set([x.get('id') for x in res])
        res_clumped = []
        for outcome in found_outcomes:
            logger.debug("clumping results for " + str(outcome))
            rsid = [x.get('rsid') for x in res if x.get('id') == outcome]
            p = [x.get('p') for x in res if x.get('id') == outcome]
            out = plink_clumping_rs(Globals.TMP_FOLDER, rsid, p, pval, pval, r2, kb)
            res_clumped = res_clumped + [x for x in res if x.get('id') == outcome and x.get('rsid') in out]
        return res_clumped
    res = add_trait_to_result(res, study_data)
    return res
