from flask_restful import Api, Resource, reqparse, abort
from flask import request
from _globals import *
from _logger import *
from _auth import *
from _es import *


class Phewas(Resource):
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
			print e
			abort(503)
		return {'data':out}

	def post(self):
		logger_info()
		parser = reqparse.RequestParser()
		parser.add_argument('rsid', required=False, type=str, action='append', default=[], help="List of SNP rs IDs")
		args = parser.parse_args()
		try:
			user_email = get_user_email(request.headers.get('X-Api-Token'))
			out = query_summary_stats(
				user_email,
				",".join([ "'" + x + "'" for x in args['rsid']]),
				"snp_lookup"
			)
		except Exception as e:
			print e
			abort(503)
		return {'data':out}


