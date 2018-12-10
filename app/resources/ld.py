from flask_restful import Api, Resource, reqparse, abort
from _globals import *
from _logger import *
from _ld import *

class Clump(Resource):
	def post(self):
		logger_info()
		parser = reqparse.RequestParser()
		parser.add_argument('rsid', type=str, required=False, action='append', default=[])
		parser.add_argument('pval', type=float, required=False, action='append', default=[])
		parser.add_argument('pthresh', type=float, required=False, default=5e-8)
		parser.add_argument('r2', type=float, required=False, default=0.001)
		parser.add_argument('kb', type=int, required=False, default=5000)
		args = parser.parse_args()
		if(len(args['rsid']) == 0):
			abort(405)
		if(len(args['pval']) == 0):
			abort(405)
		if(len(args['rsid']) != len(args['pval'])):
			abort(405)

		try:
			out = plink_clumping_rs(TMP_FOLDER, args['rsid'], args['pval'], args['pthresh'], args['pthresh'], args['r2'], args['kb'])
		except:
			abort(503)
		return out, 200

class LdMatrix(Resource):
	def post(self):
		logger_info()
		parser = reqparse.RequestParser()
		parser.add_argument('rsid', required=False, type=str, action='append', default=[])
		parser.add_argument('p1', type=float, required=False, default=5e-8)
		parser.add_argument('r2', type=float, required=False, default=0.001)
		parser.add_argument('kb', type=int, required=False, default=5000)
		args = parser.parse_args()
		try:
			out = plink_ldsquare_rs(TMP_FOLDER, args['rsid'])
		except:
			abort(503)
		return out, 200


