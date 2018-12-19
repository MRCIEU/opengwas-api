import urllib
import PySQLPool
import json
from flask_restplus import Resource, reqparse, abort, Namespace, fields
from flask import request
from _globals import *
from _auth import *
from _logger import *

api = Namespace('gwasinfo', description="Get information about available GWAS summary datasets")



@api.route('/list')
@api.doc(description="Return all available GWAS summary datasets")
class GwasList(Resource):
	def get(self):
		logger_info()
		access_query = email_query(get_user_email(request.headers.get('X-Api-Token')))
		SQL = """SELECT * FROM study_e c WHERE {0}""".format(access_query)
		try:
			query = PySQLPool.getNewQuery(dbConnection)
			query.Query(SQL)
		except:
			abort(503)
		return query.record, 200


@api.route('/<id>')
@api.doc(
	description="Get information about specified GWAS summary datasets",
	params={'id': 'An ID or comma-separated list of IDs'}
)
class GwasInfoGet(Resource):
	def get(self, id=None):
		logger_info()
		access_query = email_query(get_user_email(request.headers.get('X-Api-Token')))
		id_query = "','".join(id.split(',')).replace(';','')
		SQL =  """SELECT * FROM study_e c WHERE c.id IN
			('{0}') AND {1}""".format(id_query, access_query)
		try:
			query = PySQLPool.getNewQuery(dbConnection)
			query.Query(SQL)
		except:
			abort(503)
		return query.record, 200


parser = reqparse.RequestParser()
parser.add_argument('id', required=True, type=str, action='append', default=[], help="List of IDs")

# idfield = api.model('IdList', {
# 	'id': fields.List(fields.String)
# })

@api.route('/', methods=["post"])
@api.doc(
	description="Get information about specified GWAS summary datasets")
class GwasInfoPost(Resource):
	@api.expect(parser)
	def post(self):
		logger_info()
		args = parser.parse_args()
		access_query = email_query(get_user_email(request.headers.get('X-Api-Token')))
		if(len(args['id']) == 0):
			SQL = """SELECT * FROM study_e c WHERE {0}""".format(access_query)
		else:
			id_query = "','".join(args['id']).replace(';','')
			SQL = """SELECT * FROM study_e c WHERE c.id IN ('{0}') AND {1}""".format(id_query, access_query)
		try:
			query = PySQLPool.getNewQuery(dbConnection)
			query.Query(SQL)
		except:
			abort(503)
		return query.record, 200

