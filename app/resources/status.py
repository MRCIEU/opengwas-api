import os
from flask_restful import Api, Resource
from flask import request
from _globals import *
from _logger import *
import requests

class Status(Resource):
	def get(self):
		logger_info()
		
		out = {
			'API version': VERSION, 
			'Number of GWAS in MySQL': check_mysql(),
			'ElasticSearch status': check_elastic(),
			'LD reference panel': check_ld_ref(),
			'PLINK executable': check_plink()
		}
		return out

def check_ld_ref():
	if(os.path.isfile(LD_REF+".bed") and os.path.isfile(LD_REF+".bim") and os.path.isfile(LD_REF+".fam")):
		return "Available"
	else:
		return 'Unavailable'

def check_plink():
	if os.popen(PLINK + " --version").read().split("\n")[0] == '':
		return 'Unavailable'
	else:
		return "Available"

def check_elastic():
	try:
		out = requests.get(es_conf['host'] + ':' + es_conf['port'] + '/_cluster/health?pretty').json()
		if out['status'] == 'red':
			return "Available"
		else:
			return "Unavailable"
	except:
		return "Unavailable"

def check_mysql():
	SQL   = "show databases;"
	# SQL   = "SELECT COUNT(*) FROM study_e;"
	try:
		query = PySQLPool.getNewQuery(dbConnection)
		query.Query(SQL)
		if len(query.record) > 0:
			return "Available"
		else:
			return "Unavailable"
	except:
		return "Unavailable"
