from flask_restplus import Resource, reqparse, abort, Namespace, fields
from flask import request
from _globals import *
from _logger import *
from _auth import *
from _es import *


api = Namespace('associations', description="Retrieve GWAS associations")

parser1 = api.parser()
parser1.add_argument(
'X-Api-Token', location='headers', required=False, default='null', help='Public datasets can be queried without any authentication, but some studies are only accessible by specific users. To authenticate we use Google OAuth2.0 access tokens. The easiest way to obtain an access token is through the [TwoSampleMR R](https://mrcieu.github.io/TwoSampleMR/#authentication) package using the `get_mrbase_access_token()` function.')

@api.route('/<id>/<rsid>')
@api.expect(parser1)
@api.doc(
	description="Get specific SNP associations for specifc GWAS datasets",
	params={
	'id': 'An ID or comma-separated list of GWAS dataset IDs',
	'rsid': 'Comma-separated list of rs IDs to query from the GWAS IDs'
	}
)
class AssocGet(Resource):
	def get(self, id=None, rsid=None):
		logger_info()
		if rsid is None:
			abort(404)
		if id is None:
			abort(404)
		try:
			user_email = get_user_email(request.headers.get('X-Api-Token'))
			out = query_summary_stats(
				user_email, 
				",".join([ "'" + x + "'" for x in rsid.split(',')]), 
				",".join([ "'" + x + "'" for x in id.split(',')])
			)
		except:
			abort(503)
		return out



parser2 = reqparse.RequestParser()
parser2.add_argument('rsid', required=False, type=str, action='append', default=[], help="List of SNP rs IDs")
parser2.add_argument('id', required=False, type=str, action='append', default=[], help="list of MR-Base GWAS study IDs")
parser2.add_argument('proxies', type=int, required=False, default=0, help="Whether to look for proxies (1) or not (0)")
parser2.add_argument('r2', type=float, required=False, default=0.8, help="Minimum LD r2 for a proxy")
parser2.add_argument('align_alleles', type=int, required=False, default=1, help="Whether to align alleles")
parser2.add_argument('palindromes', type=int, required=False, default=1, help="Whether to allow palindromic proxies")
parser2.add_argument('maf_threshold', type=float, required=False, default=0.3, help="Maximum MAF allowed for a palindromic variant")
parser2.add_argument(
'X-Api-Token', location='headers', required=False, default='null', help='Public datasets can be queried without any authentication, but some studies are only accessible by specific users. To authenticate we use Google OAuth2.0 access tokens. The easiest way to obtain an access token is through the [TwoSampleMR R](https://mrcieu.github.io/TwoSampleMR/#authentication) package using the `get_mrbase_access_token()` function.')

@api.route('/')
@api.doc(
	description="""
Get specific SNP associations for specifc GWAS datasets. Note the payload can be passed to curl via json using:

```
-X POST -d '
{
    'id': ['2','1001']
}
'
```

"""
)
class AssocPost(Resource):
	@api.expect(parser2)
	def post(self):
		logger_info()
		args = parser2.parse_args()

		if(len(args['id']) == 0):
			abort(405)

		if(len(args['rsid']) == 0):
			abort(405)

		try:
			user_email = get_user_email(request.headers.get('X-Api-Token'))
			out = get_assoc(user_email, args['rsid'], args['id'], args['proxies'], args['r2'], args['align_alleles'], args['palindromes'], args['maf_threshold'])
		except:
			abort(503)
		return out, 200
