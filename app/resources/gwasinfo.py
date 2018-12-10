import urllib
import PySQLPool
import json
from flask_restful import Api, Resource, reqparse, abort
from flask import request
from _globals import *
from _auth import *
from _logger import *


# Abstract the query
# Return a list of the call and also the 


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

	def post(self):
		logger_info()
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

