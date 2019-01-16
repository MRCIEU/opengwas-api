from flask_restplus import Resource, reqparse, abort, Namespace, fields
from flask import request
from resources._globals import *
from resources._logger import *
from resources._auth import *
from resources._es import *


api = Namespace('phewas', description="Perform PheWAS of specified SNPs across all available GWAS datasets")

parser1 = api.parser()
parser1.add_argument(
'X-Api-Token', location='headers', required=False, default='null', help='Public datasets can be queried without any authentication, but some studies are only accessible by specific users. To authenticate we use Google OAuth2.0 access tokens. The easiest way to obtain an access token is through the [TwoSampleMR R](https://mrcieu.github.io/TwoSampleMR/#authentication) package using the `get_mrbase_access_token()` function.')

@api.route('/<rsid>')
@api.expect(parser1)
@api.doc(
	description="Perform PheWAS of specified SNPs across all available GWAS datasets",
	params={
	'rsid': 'Comma-separated list of rs IDs to query from the GWAS IDs'
	}
)
class PhewasGet(Resource):
	def get(self, rsid=None):
		logger_info()
		if rsid is None:
			abort(404)
		try:
			user_email = get_user_email(request.headers.get('X-Api-Token'))
			out = query_summary_stats(
				user_email,
				",".join([ "'" + x + "'" for x in rsid.split(',')]),
				"snp_lookup"
			)
		except Exception as e:
			print(e)
			abort(503)
		return {'data':out}

parser2 = reqparse.RequestParser()
parser2.add_argument('rsid', required=False, type=str, action='append', default=[], help="List of SNP rs IDs")
parser2.add_argument(
'X-Api-Token', location='headers', required=False, default='null', help='Public datasets can be queried without any authentication, but some studies are only accessible by specific users. To authenticate we use Google OAuth2.0 access tokens. The easiest way to obtain an access token is through the [TwoSampleMR R](https://mrcieu.github.io/TwoSampleMR/#authentication) package using the `get_mrbase_access_token()` function.')

@api.route('/')
@api.doc(
	description="""
Perform PheWAS of specified SNPs across all available GWAS datasets. Note the payload can be passed to curl via json using:

```
-X POST -d '
{
    'rsid': ['rs234']
}
'
```

"""
)
class PhewasPost(Resource):
	@api.expect(parser2)
	def post(self):
		logger_info()
		args = parser2.parse_args()
		try:
			user_email = get_user_email(request.headers.get('X-Api-Token'))
			out = query_summary_stats(
				user_email,
				",".join([ "'" + x + "'" for x in args['rsid']]),
				"snp_lookup"
			)
		except Exception as e:
			print(e)
			abort(503)
		return {'data':out}


