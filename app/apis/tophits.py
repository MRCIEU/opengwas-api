from flask_restplus import Resource, reqparse, abort, Namespace
from queries.es import *
from resources._ld import *
from queries.cql_queries import *

api = Namespace('tophits', description="Extract tophits from a GWAS dataset")

parser1 = api.parser()
parser1 = reqparse.RequestParser()
parser1.add_argument('id', required=False, type=str, action='append', default=[], help="list of MR-Base GWAS study IDs")
parser1.add_argument('pval', type=float, required=False, default=5e-8, help='P-value threshold')
parser1.add_argument('clump', type=int, required=False, default=1, help='Whether to clump (1) or not (0)')
parser1.add_argument('r2', type=float, required=False, default=0.001, help='Clumping parameter')
parser1.add_argument('kb', type=int, required=False, default=5000, help='Clumping parameter')
parser1.add_argument(
    'X-Api-Token', location='headers', required=False, default='null',
    help='Public datasets can be queried without any authentication, but some studies are only accessible by specific users. To authenticate we use Google OAuth2.0 access tokens. The easiest way to obtain an access token is through the [TwoSampleMR R](https://mrcieu.github.io/TwoSampleMR/#authentication) package using the `get_mrbase_access_token()` function.')


@api.route('')
@api.doc(
    description="""
Extract tophits from a GWAS dataset. Note the payload can be passed to curl via json using:

```
-X POST -d '
{
    'parameters':'etc'
}
'
```
""")
class Tophits(Resource):
    @api.expect(parser1)
    def post(self):
        logger_info()
        args = parser1.parse_args()

        user_email = get_user_email(request.headers.get('X-Api-Token'))

        try:
            out = extract_instruments(user_email, args['id'], args['clump'], args['pval'], args['r2'], args['kb'])
        except:
            abort(503)
        return out


def extract_instruments(user_email, id, clump, pval, r2, kb):
    ### elastic query
    # fix outcomes
    outcomes = ",".join(["'" + x + "'" for x in id])
    outcomes_clean = outcomes.replace("'", "")
    # get available studies
    study_access = set(get_all_gwas_ids_for_user(user_email))
    # logger2.debug(sorted(study_access))
    logger2.debug('searching ' + outcomes_clean)
    outcomes_access = []
    for o in outcomes_clean.split(','):
        if o in study_access:
            outcomes_access.append(o)
        else:
            logger2.debug(o + " not in access_list")
    if len(outcomes_access) == 0:
        logger2.debug('No outcomes left after permissions check')
        return json.dumps([], ensure_ascii=False)
    else:
        ESRes = elastic_query(snps='', studies=outcomes_access, pval=pval)
        # logger2.debug(ESRes)
        snpDic = {}
        # create lookup for snp names
        for s in ESRes:
            hits = ESRes[s]['hits']['hits']
            for hit in hits:
                snpDic[hit['_source']['snp_id']] = ''

        # get study and snp data
        # study_data = study_info([outcomes])[outcomes]
        study_data = study_info(outcomes)
        # snp_data = snp_info(snpDic.keys(),'id_to_rsid')
        snp_data = snpDic.keys()

        # create final file
        numRecords = 0
        res = []
        for s in ESRes:
            hits = ESRes[s]['hits']['hits']
            numRecords += int(ESRes[s]['hits']['total'])
            for hit in hits:
                other_allele = effect_allele = effect_allele_freq = beta = se = p = n = ''
                if hit['_source']['effect_allele_freq'] < 999:
                    effect_allele_freq = hit['_source']['effect_allele_freq']
                if hit['_source']['beta'] < 999:
                    # beta = "%4.3f" % float(hit['_source']['beta'])
                    beta = hit['_source']['beta']
                if hit['_source']['se'] < 999:
                    # se = "%03.02e" % float(hit['_source']['se'])
                    se = hit['_source']['se']
                if hit['_source']['p'] < 999:
                    # p = "%03.02e" % float(hit['_source']['p'])
                    p = hit['_source']['p']
                if 'n' in hit['_source']:
                    n = hit['_source']['n']
                if 'effect_allele' in hit['_source']:
                    effect_allele = hit['_source']['effect_allele']
                if 'other_allele' in hit['_source']:
                    other_allele = hit['_source']['other_allele']
                name = hit['_source']['snp_id']
                # logger2.debug(hit)
                # don't want data with no pval
                if p != '':
                    assocDic = {'effect_allele': effect_allele,
                                'other_allele': other_allele,
                                'effect_allelel_freq': effect_allele_freq,
                                'beta': beta,
                                'se': se,
                                'p': p,
                                'n': n,
                                'name': name
                                }
                    study_id = hit['_source']['study_id']
                    if s != mrb_batch:
                        study_id = s + ':' + hit['_source']['study_id']
                    # make sure only to return available studies
                    if study_id in study_data:
                        assocDic.update(study_data[study_id])
                        # logger2.debug(assocDic)
                        # res.append(study_data)
                        res.append(assocDic)
        studies = outcomes.strip().split(",")
        nsnps = len(res)

        if clump == 1 and numRecords != 0:
            found_outcomes = set([x.get('id') for x in res])
            all_out = []
            for outcome in found_outcomes:
                logger2.debug("clumping results for " + str(outcome))
                rsid = [x.get('name') for x in res if x.get('id') == outcome]
                p = [x.get('p') for x in res if x.get('id') == outcome]
                out = plink_clumping_rs(TMP_FOLDER, rsid, p, pval, pval, r2, kb)
                all_out = all_out + [x for x in res if x.get('id') == outcome and x.get('name') in out]

            return all_out

        return res
