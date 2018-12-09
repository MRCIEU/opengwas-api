import os
from flask_restful import Api, Resource
from flask import request
from _globals import *
from _logger import *

class Status(Resource):
	def get(self):
		headers = request.headers
		print(headers.get('Host'))
		SQL   = "SELECT COUNT(*) FROM study_e;"
		query = PySQLPool.getNewQuery(dbConnection)
		query.Query(SQL)
		logger.info("Testing logger")
		logger2.debug("Testing logger2")
		out = {
			'API version': VERSION, 
			'Number of GWAS in MySQL': query.record[0]['COUNT(*)'],
			'ElasticSearch status': 'Do something to test elasticsearch',
			'LD reference panel': check_ld_ref(LD_REF),
			'PLINK executable': check_plink(PLINK)
		}
		return out

def check_ld_ref(ldref):
	if(os.path.isfile(ldref+".bed") and os.path.isfile(ldref+".bim") and os.path.isfile(ldref+".fam")):
		return ldref
	else:
		return 'Reference unavailable'

def check_plink(plink):
	return os.popen(plink + " --version").read().split("\n")[0]
