from flask_restplus import Resource, reqparse, abort, Namespace
from queries.variants import *
from resources.auth import get_user_email
from flask import request

api = Namespace('variants', description="Retrieve variant information")


@api.route('/rsid/<rsid>')
@api.doc(
    description="Obtain information for a particular SNP or comma separated list of SNPs",
    params={
        'rsid': 'Comma-separated list of rs IDs to query from the GWAS IDs'
    }
)
class VariantGet(Resource):
    def get(self, rsid=None):
        if rsid is None:
            abort(404)
        try:
            total, hits = snps(rsid.split(','))
        except Exception as e:
            logger.error("Could not obtain variant information: {}".format(e))
            abort(503)
        return {"total":total,"results":hits}


parser2 = reqparse.RequestParser()
parser2.add_argument('rsid', required=False, type=str, action='append', default=[], help="List of variant rs IDs")
parser2.add_argument('chrpos', required=False, type=str, action='append', default=[], help="List of variant chr:pos format on build 37 (e.g. 7:105561135)")

@api.route('/rsid')
@api.doc(
    description="""
Obtain information for a particular SNP or comma separated list of SNPs. Note the payload can be passed to curl via json using e.g.:

```
-X POST -d '
{
    'rsid': ['rs234','rs333']
}
'
```

"""
)
class VariantPost(Resource):
    @api.expect(parser2)
    def post(self):
        args = parser2.parse_args()

        if (len(args['rsid']) == 0):
            abort(405)
        try:
            total, hits = snps(args['rsid'])
        except Exception as e:
            logger.error("Could not obtain variant information: {}".format(e))
            abort(503)
        return {"total":total,"results":hits}



parser1 = reqparse.RequestParser()
parser1.add_argument('radius', type=int, required=False, default=0, help="Range to search either side of target locus")

@api.route('/chrpos/<int:chr>/<int:pos>')
@api.expect(parser1)
@api.doc(
    description="Obtain information for a particular SNP or comma separated list of SNPs",
    params={
        'chr': 'B37 chromosome',
        'pos': 'B37 position'
    }
)
class RangeGet(Resource):
    def get(self, chr=None, pos=None, radius=0):
        args = parser1.parse_args()
        try:
            total, hits = range_query(chr, pos, args['radius'])
        except Exception as e:
            logger.error("Could not obtain variant information: {}".format(e))
            abort(503)
        return {"total":total,"results":hits}




@api.route('/gene/<gene>')
@api.expect(parser1)
@api.doc(
    description="Obtain information for a particular SNP or comma separated list of SNPs",
    params={
        'gene': "A gene identifier, either Ensembl or Entrez, e.g. ENSG00000123374 or 1017"
    }
)
class GeneGet(Resource):
    def get(self, gene=None):
        args = parser1.parse_args()
        try:
            total, hits = gene_query(gene, args['radius'])
        except Exception as e:
            logger.error("Could not obtain variant information: {}".format(e))
            abort(503)
        return {"total":total,"results":hits}




# parser2 = reqparse.RequestParser()
# parser2.add_argument('rsid', required=False, type=str, action='append', default=[], help="List of SNP rs IDs")
# parser2.add_argument('id', required=False, type=str, action='append', default=[], help="list of MR-Base GWAS study IDs")
# parser2.add_argument('proxies', type=int, required=False, default=0, help="Whether to look for proxies (1) or not (0)")
# parser2.add_argument('r2', type=float, required=False, default=0.8, help="Minimum LD r2 for a proxy")
# parser2.add_argument('align_alleles', type=int, required=False, default=1, help="Whether to align alleles")
# parser2.add_argument('palindromes', type=int, required=False, default=1, help="Whether to allow palindromic proxies")
# parser2.add_argument('maf_threshold', type=float, required=False, default=0.3,
#                      help="Maximum MAF allowed for a palindromic variant")
# parser2.add_argument(
#     'X-Api-Token', location='headers', required=False, default='null',
#     help='Public datasets can be queried without any authentication, but some studies are only accessible by specific users. To authenticate we use Google OAuth2.0 access tokens. The easiest way to obtain an access token is through the [TwoSampleMR R](https://mrcieu.github.io/TwoSampleMR/#authentication) package using the `get_mrbase_access_token()` function.')


# @api.route('/')
# @api.doc(
#     description="""
# Get specific SNP associations for specifc GWAS datasets. Note the payload can be passed to curl via json using:

# ```
# -X POST -d '
# {
#     'id': ['2','1001']
# }
# '
# ```

# """
# )
# class AssocPost(Resource):
#     @api.expect(parser2)
#     def post(self):
#         args = parser2.parse_args()

#         if (len(args['id']) == 0):
#             abort(405)

#         if (len(args['rsid']) == 0):
#             abort(405)

#         try:
#             user_email = get_user_email(request.headers.get('X-Api-Token'))
#             out = get_assoc(user_email, args['rsid'], args['id'], args['proxies'], args['r2'], args['align_alleles'],
#                             args['palindromes'], args['maf_threshold'])
#         except Exception as e:
#             logger.error("Could not obtain SNP association: {}".format(e))
#             abort(503)
#         return out, 200
