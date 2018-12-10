from flask_restful import Api, Resource, reqparse, abort
from flask import request
from _globals import *
from _logger import *
from _auth import *
from _es import *


class Assoc(Resource):
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

	def post(self):
		logger_info()
		parser = reqparse.RequestParser()
		parser.add_argument('rsid', required=False, type=str, action='append', default=[], help="List of SNP rs IDs")
		parser.add_argument('id', required=False, type=str, action='append', default=[], help="list of MR-Base GWAS study IDs")
		parser.add_argument('proxies', type=int, required=False, default=0)
		parser.add_argument('r2', type=float, required=False, default=0.8)
		parser.add_argument('align_alleles', type=int, required=False, default=1)
		parser.add_argument('palindromes', type=int, required=False, default=1)
		parser.add_argument('maf_threshold', type=float, required=False, default=0.3)
		args = parser.parse_args()

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
