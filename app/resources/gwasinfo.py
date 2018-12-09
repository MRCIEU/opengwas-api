import urllib
import PySQLPool
import json
from flask_restful import Api, Resource, reqparse, abort
from _globals import *
from _auth import *


# Abstract the query
# Return a list of the call and also the 

class GwasInfoList(Resource):
	def get(self):
		access_query = token_query('NULL')
		SQL = """SELECT * FROM study_e c WHERE {0}""".format(access_query)
		try:
			query = PySQLPool.getNewQuery(dbConnection)
			query.Query(SQL)
		except:
			abort(503)
		return query.record, 200

	def post(self):
		parser = reqparse.RequestParser()
		parser.add_argument('id', required=False, type=str, action='append', default=[])
		parser.add_argument('access_token', required=False, default='NULL', location='json')
		args = parser.parse_args()
		access_query = token_query(args['access_token'])
		id_query = "','".join(args['id']).replace(';','')
		SQL = """SELECT * FROM study_e c WHERE c.id IN ('{0}') AND {1}""".format(id_query, access_query)
		try:
			query = PySQLPool.getNewQuery(dbConnection)
			query.Query(SQL)
		except:
			abort(503)
		return query.record, 200



class GwasInfo(Resource):
	def get(self, id):
		access_query = token_query('NULL')
		id_query = "','".join(id.split(',')).replace(';','')
		SQL =  """SELECT * FROM study_e c WHERE c.id IN
			('{0}') AND {1}""".format(id_query, access_query)
		try:
			query = PySQLPool.getNewQuery(dbConnection)
			query.Query(SQL)
		except:
			abort(503)
		return query.record, 200

