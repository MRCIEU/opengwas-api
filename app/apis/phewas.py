from flask_restplus import Resource, reqparse, abort, Namespace
from queries.es import *
from resources.auth import get_user_email
from flask import request
from resources.globals import Globals

api = Namespace('phewas', description="Perform PheWAS of specified SNPs across all available GWAS datasets")

parser1 = api.parser()
parser1.add_argument(
    'X-Api-Token', location='headers', required=False, default='null',
    help=Globals.AUTHTEXT)


@api.route('/<rsid>/<pval>')
@api.expect(parser1)
@api.doc(
    description="Perform PheWAS of specified SNPs across all available GWAS datasets",
    params={
        'rsid': 'Comma-separated list of rs IDs to query from the GWAS IDs',
        'pval': 'P-value threshold'
    }
)
class PhewasGet(Resource):
    def get(self, rsid=None, pval=1e-3):
        if rsid is None:
            abort(404)
        try:
            outFilter=[]
            user_email = get_user_email(request.headers.get('X-Api-Token'))
            out = query_summary_stats(
                user_email,
                rsid.split(','),
                "snp_lookup"
            )
            logger.debug('Filtering phewas: '+str(pval))
            for d in out:
                if float(d['p'])<float(pval):
                    outFilter.append(d)
            logger.debug('Size after filtering: '+str(len(outFilter)))
        except Exception as e:
            logger.error("Could not query summary stats: {}".format(e))
            abort(503)
        return {'data': outFilter}


parser2 = reqparse.RequestParser()
parser2.add_argument('rsid', required=False, type=str, action='append', default=[], help="List of SNP rs IDs")
parser2.add_argument('pval', type=float, required=False, default=1e-05, help='P-value threshold')
parser2.add_argument(
    'X-Api-Token', location='headers', required=False, default='null',
    help=Globals.AUTHTEXT)


@api.route('')
@api.doc(
    description="""
Perform PheWAS of specified SNPs across all available GWAS datasets. Note the payload can be passed to curl via json using:

```
-X POST -d '
{
    'rsid': ['rs234'],
    'pval': '1e-05'
}
'
```

"""
)
class PhewasPost(Resource):
    @api.expect(parser2)
    def post(self):
        args = parser2.parse_args()
        try:
            outFilter=[]
            user_email = get_user_email(request.headers.get('X-Api-Token'))
            out = query_summary_stats(
                user_email,
                args['rsid'],
                "snp_lookup"
            )
            logger.debug('Filtering phewas'+str(args['pval']))
            for d in out:
                if float(d['p'])<args['pval']:
                    outFilter.append(d)
            logger.debug('Size after filtering: '+str(len(outFilter)))
        except Exception as e:
            logger.error("Could not query summary stats: {}".format(e))
            abort(503)
        return {'data': outFilter}
