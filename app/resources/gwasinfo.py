import urllib
import PySQLPool
import json
from flask_restful import Api, Resource, reqparse, abort
from _globals import *
from _auth import *


# Abstract the query
# Return a list of the call and also the 

class GwasListAuth(Resource):
	def get(self, token):
		access_query = email_query(get_user_email(token))
		
		SQL = """SELECT * FROM study_e c WHERE {0}""".format(access_query)
		try:
			query = PySQLPool.getNewQuery(dbConnection)
			query.Query(SQL)
		except:
			abort(503)
		return query.record, 200

class GwasList(Resource):
	def get(self, token='NULL'):
		access_query = email_query(get_user_email(token))
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



class GwasInfo(Resource):
	def get(self, id):
		access_query = email_query(get_user_email(token))
		id_query = "','".join(id.split(',')).replace(';','')
		SQL =  """SELECT * FROM study_e c WHERE c.id IN
			('{0}') AND {1}""".format(id_query, access_query)
		try:
			query = PySQLPool.getNewQuery(dbConnection)
			query.Query(SQL)
		except:
			abort(503)
		return query.record, 200

