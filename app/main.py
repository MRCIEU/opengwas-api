import os
import sys
import json
import urllib
import PySQLPool
import subprocess
import re
import tempfile
import uuid
import csv
import string
from optparse import *
from flask import *
from werkzeug import secure_filename
import logging
import logging.handlers
import sqlite3 as sqli
import datetime
from elasticsearch import Elasticsearch
import time
from flask import current_app

#cache
#from flask import Flask
#from flask_cache import Cache
#from flask_caching import Cache

app = Flask(__name__)
# Check Configuring Flask-Cache section for more details
#cache = Cache()
#CACHE_TYPE='simple'
#cache = Cache(app, config={'CACHE_TYPE': 'uwsgi','CACHE_UWSGI_NAME':'mycache@localhost'})
#cache = Cache(app,config={'CACHE_TYPE': 'filesystem','CACHE_DIR':'/tmp'})
#cache = Cache(app,config={'CACHE_TYPE': 'simple'})
#cache.init_app(app)
#CACHE_DIR='/tmp/'

# get flask_cache logger
#flask_cache_logger = logging.getLogger('flask_caching')
# set up a handler
#formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
#stderr_handler = logging.StreamHandler(sys.stderr)
#stderr_handler.setFormatter(formatter)
# add the handler
#flask_cache_logger.addHandler(stderr_handler)

#unicode issues
reload(sys)
sys.setdefaultencoding('utf8')

#changes
#1. removed mysql queries to assoc table and replace with elasticsearch
#2. removed clean_outcome_string for outcomes due to new IDs with prefix

"""

Constants

"""

OAUTH2_URL = 'https://www.googleapis.com/oauth2/v1/tokeninfo?access_token='
USERINFO_URL = 'https://www.googleapis.com/oauth2/v1/userinfo?alt=json&access_token='
UPLOAD_FOLDER = './tmp/'
ALLOWED_EXTENSIONS = set(['txt'])
MAX_FILE_SIZE = 16 * 1024 * 1024

LOG_FILE = "./logs/mrbaseapi.log"
LOG_FILE_DEBUG = "./logs/mrbaseapi-debug.log"
CENTRAL_DB = "./conf_files/central.json"
MYSQL_DB = "./conf_files/mysql.json"
DOCKER_DB = "./conf_files/dockerswarm.json"
UCSC_DB = "./conf_files/ucsc.json"
ORIGINAL_DB = "./conf_files/original.json"
APICALL_LOG_FILE = "./logs/mrbaselog.sqlite"
ES_CONF = "./conf_files/es_conf.json"

"""

Setup logging

"""

class ContextFilter(logging.Filter):
    """
    This is a filter which injects contextual information into the log.
    """
    def filter(self, record):
        token = request.args.get('access_token')
        record.user = get_user_email(token)
        #record.ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr).split(',')[0]

        #print record.user
        return True


if not os.path.exists(LOG_FILE):
	open('file', 'w').close()

formatter=logging.Formatter('%(asctime)s %(msecs)d %(user)s %(threadName)s %(levelname)s [%(filename)s:%(lineno)d] %(message)s',datefmt='%d-%m-%Y:%H:%M:%S')

def setup_logger(name, log_file, level=logging.INFO):
	# Create the log message rotatin file handler to the logger
	# 10000000 = 10 MB
	handler = logging.handlers.RotatingFileHandler(log_file,maxBytes=10000000, backupCount=100)
	handler.setFormatter(formatter)

	logger = logging.getLogger(name)
	logger.setLevel(level)
	logger.addHandler(handler)

	#add user email to all log messages
	user_email=ContextFilter()
	logger.addFilter(user_email)

	return logger

#create info log
logger = setup_logger('info-log', LOG_FILE)
#create debug log
logger2 = setup_logger('debug-log', LOG_FILE_DEBUG, level=logging.DEBUG)
#logger2.disabled = True

"""

Initialise app

"""


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE
#app.debug = True


"""

CONNECT TO DATABASES

Two MR-Base databases - original server much be connected through tunnel
					  - central server goes through SSL

UCSC - This may not be required anymore

----

The following code tests the MR-Base database connection

dbConnection = PySQLPool.getNewConnection(**mrbase_config)
SQL   = "describe study;"
query = PySQLPool.getNewQuery(dbConnection)
query.Query(SQL)
json.dumps(query.record)


"""

with open(ES_CONF) as f:
	es_conf = json.load(f)

#with open(DOCKER_DB) as f:
#    mrbase_config = json.load(f)

#with open(CENTRAL_DB) as f:
with open(MYSQL_DB) as f:
	mrbase_config = json.load(f)

# with open(ORIGINAL_DB) as f:
#    mrbase_config = json.load(f)

with open(UCSC_DB) as f:
	ucsc_config = json.load(f)


dbConnection = PySQLPool.getNewConnection(**mrbase_config)
ucscConnection = PySQLPool.getNewConnection(**ucsc_config)

#connect to elasticsearch
es = Elasticsearch(
		[{'host': es_conf['host'],'port': es_conf['port']}],
		#http_auth=(es_conf['user'], es_conf['password']),
)

es_timeout=120

"""

Get study batches

"""

mrb_batch='MRB'
study_batches=[mrb_batch,'UKB-a','UKB-b','UKB-c','pQTL-a','eqtl-a']
private_batches=['pQTL-a','eqtl-a','UKB-c']

"""

General functions

"""


def check_filename(strg, search=re.compile(r'[^a-z0-9.]').search):
	return not bool(search(strg))

def clean_snp_string(snpstring):
	# Function to clean snp string of bad characters
	snpstring = snpstring.encode("ascii")
	transtable = string.maketrans('','')
	rsidallowed = "rs,0123456789" # Remove all characters except these (including white space)
	cleansnp = transtable.translate(transtable,rsidallowed)
	return snpstring.translate(transtable,cleansnp)

def clean_outcome_string(outcomestring):
	# Function to clean outcome string of bad characters
	outcomestring = outcomestring.encode("ascii")
	transtable = string.maketrans('','')
	rsidallowed = ",0123456789" # Allow numeric IDs and commas only
	cleansnp = transtable.translate(transtable,rsidallowed)
	return outcomestring.translate(transtable,cleansnp)

#removed clean_outcome_string for outcomes due to new IDs with prefix
def joinarg(field):
	field_text = ""
	if field == "outcomes":
		#field_text = clean_outcome_string(request.args.get(field))
		field_text = request.args.get(field)
	elif field == "snps":
		field_text = clean_snp_string(request.args.get(field))
	#else: field_text = request.args.get(field) # Unsafe
	return ",".join([ "'" + x + "'" for x in field_text.split(",") ])

def joinarray(array):
	return ",".join([ "'" + str(x) + "'" for x in array])

def allowed_file(filename):
	return '.' in filename and \
		   filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


"""

Authentication and logging functions

"""


def get_user_email(token):
	url = OAUTH2_URL + str(token)
	response = urllib.urlopen(url)
	data = json.loads(response.read())
	if "email" in data:
		return data['email']
	else:
		return token
                #return "NULL"

def check_access_token(token):
	url = OAUTH2_URL + token
	response = urllib.urlopen(url)
	data = json.loads(response.read())
	if "email" in data:
		if check_email(data['email']):
			return "internal"
		else:
			return "conditional"
	else:
		return "public"


def token_query(token):
	user_email = get_user_email(token)
	logger2.debug("getting credentials for "+user_email)
	query =  """(c.id IN (select d.id from study_e d, memberships m, permissions_e p
					WHERE m.uid = "{0}"
					AND p.gid = m.gid
					AND d.id = p.study_id
				)
				OR c.id IN (select d.id from study_e d, permissions_e p
					WHERE p.gid = 1
					AND d.id = p.study_id
				))""".format(user_email)
	#logger2.debug(query)
	return query

#create list of studies available to user
def token_query_list(token):
	qList = []
	user_email = get_user_email(token)
	logger2.debug("getting credentials for "+user_email)
        if user_email == 'AIzaSyCMFGGTR2mljNXEgYsmfHa4hK8masLxSDo':
            logger2.debug("exiting")
            sys.exit()
	SQL =  """select id from study_e c where (c.id IN (select d.id from study_e d, memberships m, permissions_e p
		WHERE m.uid = "{0}"
		AND p.gid = m.gid
		AND d.id = p.study_id
		)
		OR c.id IN (select d.id from study_e d, permissions_e p
		WHERE p.gid = 1
		AND d.id = p.study_id
		))""".format(user_email)
	SQL2="""select id from study_e""".format(user_email)
	#logger2.debug(SQL)
	query = PySQLPool.getNewQuery(dbConnection)
	query.Query(SQL)
	for q  in query.record:
		qList.append(q['id'])
	logger2.debug('access to '+str(len(qList))+' studies')
	return qList


"""

Query functions

"""
#@cache.cached(timeout=50)
def query_summary_stats(token, snps, outcomes):
	#### es
	#logger2.debug('in query_summary_stats: '+str(snps)+' : '+str(outcomes))
	#get available studies
	study_access=token_query_list(token)
	#logger2.debug(study_access)
	snpList=snps.split(',')
	logger2.debug('len snplist = '+str(len(snpList)))

	#get study and snp data
	#snp_data = {}
	snp_data = snps.replace("'","").split(',')
	#if snps!='':
		#snp_data = snp_info(snpList,'rsid_to_id')
	#logger2.debug(snp_data)

	#logger2.debug(sorted(study_access))
	logger2.debug('searching '+str(len(outcomes))+' outcomes')
	logger2.debug('creating outcomes list and study_data dictionary')
	start = time.time()
	outcomes_access=[]
	outcomes_clean = outcomes.replace("'","")
	if outcomes == 'snp_lookup':
		outcomes_access = 'snp_lookup'
		study_data=study_info(outcomes)
	else:
		study_data=study_info(outcomes)
		for o in outcomes_clean.split(','):
			if o in study_access:
				outcomes_access.append(o)
			else:
				logger2.debug(o+" not in access_list")
		#logger2.debug(outcomes_access)
	end = time.time()
	t=round((end - start), 4)
	logger2.debug('took: '+str(t)+' seconds')
	logger2.debug('len study_data = '+str(len(study_data)))
	logger2.debug('len outcomes_access = '+str(len(outcomes_access)))
	if len(outcomes_access)==0 and outcomes != 'snp_lookup':
		return json.dumps([])
	#this is slower than fetching all and filtering afterwards
	#if outcomes == 'snp_lookup':
        #    ESRes = elastic_query(snps=snp_data,studies=outcomes_access,pval='1e-5')
        #else:
        #    ESRes = elastic_query(snps=snp_data,studies=outcomes_access,pval='')
	ESRes = elastic_query(snps=snp_data,studies=outcomes_access,pval='')
        es_res=[]
	for s in ESRes:
		hits = ESRes[s]['hits']['hits']

		#create final file

		for hit in hits:
			#logger2.debug(hit)
			other_allele = effect_allele = effect_allele_freq = beta = se = p = n = ''
			if hit['_source']['effect_allele_freq'] < 999:
				effect_allele_freq = hit['_source']['effect_allele_freq']
			if hit['_source']['beta'] < 999:
				#beta = "%4.3f" % float(hit['_source']['beta'])
				beta = hit['_source']['beta']
			if hit['_source']['se'] < 999:
				#se = "%03.02e" % float(hit['_source']['se'])
				se = hit['_source']['se']
			if hit['_source']['p'] < 999:
				#p = "%03.02e" % float(hit['_source']['p'])
				p = hit['_source']['p']
			if 'n' in hit['_source']:
				n = hit['_source']['n']
			if 'effect_allele' in hit['_source']:
				effect_allele = hit['_source']['effect_allele']
			if 'other_allele' in hit['_source']:
				other_allele = hit['_source']['other_allele']
			#name = snp_data[int(hit['_source']['snp_id'])]
			name = hit['_source']['snp_id']
			#logger2.debug(hit)
			#don't want data with no pval
			if p != '':
				assocDic = {'effect_allele':effect_allele,
					'other_allele':other_allele,
					'effect_allelel_freq':effect_allele_freq,
					'beta':beta,
					'se':se,
					'p':p,
					'n':n,
					'name':name
				}
				study_id = hit['_source']['study_id']
				if s != mrb_batch:
					study_id = s+':'+hit['_source']['study_id']
				#make sure only to return available studies
				if study_id in study_data:
					assocDic.update(study_data[study_id])
					es_res.append(assocDic)
	#logger2.debug(json.dumps(es_res,indent=4))
	logger2.debug('Total hits returned = '+str(len(es_res)))
	return es_res
	#logger2.debug(json.dumps(es_res[0],indent=4))

	#### mysql
	# start=time.time()
	# user_email = get_user_email(token)
	# access_query = token_query(token)
	# query = PySQLPool.getNewQuery(dbConnection)
	# SQL   = """SELECT a.effect_allele, a.other_allele, a.effect_allele_freq, a.beta, a.se, a.p, a.n, b.name, c.*
	# 	FROM assoc a, snp b, study c
	# 	WHERE a.snp=b.id AND a.study=c.id
	# 	AND {0}
	# 	AND a.study IN ({1})
	# 	AND b.name IN ({2})
	# 	ORDER BY a.study;""".format(access_query, outcomes, snps)
	# logger2.debug("performing summary stats query")
	# #logger2.debug(SQL)
	# nsnps = len(snps.strip().split(","))
	# studies = outcomes.strip().split(",")
	# #for study in studies:
	# #    logapicall(user_email,study,nsnps)
	# query.Query(SQL)
	# logger2.debug("done summary stats query")
	# #logger2.debug(query.record)
	# end = time.time()
	# t=round((end - start), 4)
	# logger2.debug('mysql: '+str(t)+' seconds')
	# return query.record


def get_snp_positions(snps):
	snps = ",".join([ "'" + x + "'" for x in snps ])
	ucscquery = PySQLPool.getNewQuery(ucscConnection)
	chr = ",".join([ "'chr" + str(x) + "'" for x in range(1,24)])
	SQL = "SELECT chrom, chromEnd, name " \
	"FROM snp144 " \
	"WHERE name in ({0}) " \
	"AND chrom in ({1});".format(snps, chr)
	ucscquery.Query(SQL)
	return ucscquery.record



def plink_clumping_rs(fn, upload_folder, ress, snp_col, pval_col, p1, p2, r2, kb):

	try:
		start = time.time()
		filename = upload_folder + fn + "_recode"
		tfile = open(filename, "w")
		tfile.write("SNP P\n")
		for i in xrange(len(ress)):
			tfile.write(str(ress[i].get(snp_col)) + " " + str(ress[i].get(pval_col)) + "\n")

		tfile.close()
		command =   "./ld_files/plink1.90 " \
					"--bfile ./ld_files/data_maf0.01_rs " \
					" --clump {0} " \
					" --clump-p1 {1} " \
					" --clump-p2 {2} " \
					" --clump-r2 {3} " \
					" --clump-kb {4} " \
					" --out {5}".format(filename, p1, p2, r2, kb, filename)

		logger2.debug(command)
		os.system(command)

		filename_c = filename + ".clumped"
		f = open(filename_c, "r")
		f.readline()
		words = f.read().split("\n")
		f.close()

		logger2.debug("matching clumps to original query")
		out = []
		for x in words:
			if x is not '':
				out.append([y for y in ress if y.get(snp_col) == x.split()[2]][0])
		logger2.debug("done match")
		end = time.time()
		t=round((end - start), 4)
		logger2.debug('clumping: took '+str(t)+' seconds')
	finally:
		[os.remove(os.path.join(upload_folder, f)) for f in os.listdir(upload_folder) if f.startswith(fn)]

	return out




def plink_clumping(fn, upload_folder, cp, ress, snp_col, pval_col, p1, p2, r2, kb):
	filename = upload_folder + fn + "_recode"
	try:
		tfile = open(filename, "w")
		tfile.write("SNP P\n")
		for i in xrange(len(ress)):
			y = [d.get('chrom') + ":" + str(d.get('chromEnd')) for d in cp if d.get('name') == ress[i].get(snp_col)]
			if len(y) != 0:
				y = y[0]
				ress[i]['chrpos'] = y
				tfile.write(y + " " + str(ress[i].get(pval_col)) + "\n")
		tfile.close()

		command =   "./ld_files/plink1.90 " \
					"--bfile ./ld_files/data_maf0.01 " \
					" --clump {0} " \
					" --clump-p1 {1} " \
					" --clump-p2 {2} " \
					" --clump-r2 {3} " \
					" --clump-kb {4} " \
					" --out {5}".format(filename, p1, p2, r2, kb, filename)

		logger2.debug(command)
		os.system(command)

		filename_c = filename + ".clumped"
		f = open(filename_c, "r")
		f.readline()
		words = f.read().split("\n")
		f.close()

		out = []
		for x in words:
			if x is not '':
				out.append([y for y in ress if y.get('chrpos') == x.split()[2]][0])

	finally:
		[os.remove(os.path.join(upload_folder, f)) for f in os.listdir(upload_folder) if f.startswith(fn)]

	return out


def plink_ldsquare_rs(fn, upload_folder, snps):

    try:
        filename = upload_folder + fn + "_recode"
        filenameb = upload_folder + fn + "_recode.bim"
        filenamek = upload_folder + fn + "_recode.keep"
        filenameka = upload_folder + fn + "_recode.keep.a"
        tfile = open(filename, "w")
        # tfile.write("SNP P\n")
        for i in xrange(len(snps)):
            tfile.write(str(snps[i]) + "\n")

        tfile.close()

        # Find which SNPs are present
        logger2.debug("Finding which snps are available")
        # cmd = "fgrep -wf " + filename + " ./ld_files/data_maf0.01_rs.bim > " + filenameb
        cmd =   "./ld_files/plink1.90 " \
                    "--bfile ./ld_files/data_maf0.01_rs " \
                    " --extract {0} " \
                    " --make-just-bim " \
                    " --out {1}".format(filename, filename)
        logger2.debug(cmd)
        os.system(cmd)
        cmd = "cut -d ' ' -f 1 " + filenameb + " > " + filenamek
        logger2.debug(cmd)
        os.system(cmd)
        cmd = "awk '{OFS=\"\"; print $2, \"_\", $5, \"_\", $6 }' " + filenameb + " > " + filenameka
        logger2.debug(cmd)
        os.system(cmd)
        logger2.debug("found")
        command =   "./ld_files/plink1.90 " \
                    "--bfile ./ld_files/data_maf0.01_rs " \
                    " --extract {0} " \
                    " --r square " \
                    " --out {1}".format(filenamek, filename)

        logger2.debug(command)
        os.system(command)
        filename_c = filename + ".ld"
        if not os.path.isfile(filename_c):
             logger2.debug("no file found")
             [os.remove(os.path.join(upload_folder, f)) for f in os.listdir(upload_folder) if f.startswith(fn)]
             return ['NA']

        mat = []
        f = open(filenameka, "r")
        mat.append(filter(None, f.read().split("\n")))
        f.close()

        f = open(filename_c, "r")
        for line in open(filename_c, "r").readlines():
            mat.append(line.strip("\n").split("\t"))
        f.close()

    finally:
    	# logger2.debug("finished")
        [os.remove(os.path.join(upload_folder, f)) for f in os.listdir(upload_folder) if f.startswith(fn)]

    return mat


def get_proxies(snps, chr):
	proxy_dat = []
	for i in range(len(snps)):
		fn = LD_FILES + chr[i]
		snp = snps[i]
		dat = [{'targets':snp, 'proxies': snp, 'tallele1': '', 'tallele2': '', 'pallele1': '', 'pallele2': ''}]
		logger2.debug(snp)
		flag=0
		with open(fn, "r") as f:
			alllines = f.readlines()
			for l in alllines:
				l = l.split()
				if l[2] == snp:
					flag=1
					alleles=[x[0] for x in l[6].split("/")]
					palleles=[x[-1] for x in l[6].split("/")]
					dat.append({'targets':snp,
						'proxies':l[5],
						'allele1':alleles[0],
						'allele2':alleles[1],
						'pallele1':palleles[0],
						'pallele2':palleles[1]}
					)
				elif flag == 1:
					break
		proxy_dat.append(dat)
	return proxy_dat


def get_proxies_mysql(snps, rsq, palindromes, maf_threshold):
	logger2.debug("obtaining LD proxies from mysql")
	start = time.time()
	pquery = PySQLPool.getNewQuery(dbConnection)
	if palindromes == "0":
		pal = 'AND palindromic = 0;'
	else:
		pal = "AND ( ( pmaf < " + str(maf_threshold) + " AND palindromic = 1 ) OR palindromic = 0);"
	SQL = "SELECT * " \
	"FROM proxies " \
	"WHERE target in ({0}) " \
	"AND rsq >= {1} {2} ;".format(",".join([ "'" + x + "'" for x in snps ]), rsq, pal)
	logger2.debug("performing proxy query")
	pquery.Query(SQL)
	#logger2.debug(SQL)
	logger2.debug("done proxy query")
	res = pquery.record
	proxy_dat = []
	logger2.debug("matching proxy SNPs")
	for i in range(len(snps)):
		snp = snps[i]
		dat = [{'targets':snp, 'proxies': snp, 'tallele1': '', 'tallele2': '', 'pallele1': '', 'pallele2': '', 'pal': ''}]
		#logger2.debug('total proxies = '+str(len(res)))
		for l in res:
			if l.get('target') == snp:
				#logger.info(snp+' '+l.get('proxy'))
				dat.append({
					'targets':snp,
					'proxies':l.get('proxy'),
					'tallele1':l.get('tallele1'),
					'tallele2':l.get('tallele2'),
					'pallele1':l.get('pallele1'),
					'pallele2':l.get('pallele2'),
					'pal':l.get('palindromic')}
				)
		proxy_dat.append(dat)
	logger2.debug("done proxy matching")
	end = time.time()
	t=round((end - start), 4)
	logger2.debug('proxy matching took: '+str(t)+' seconds')
	logger2.debug('returned '+str(len(proxy_dat))+' results')
	return proxy_dat

def get_proxies_es(snps, rsq, palindromes, maf_threshold):
	logger2.debug("obtaining LD proxies from ES")
	logger2.debug("palindromes "+str(palindromes))
	start = time.time()
	start = time.time()
	#pquery = PySQLPool.getNewQuery(dbConnection)
	filterData=[]
	filterData.append({"terms" : {'target':snps}})
	filterData.append({"range" : {"rsq": {"gte": str(rsq) }}})
	#logger.info(filterData)
	if palindromes == "0":
		filterData.append({"term" : {'palindromic':'0'}})
		ESRes=es.search(
			request_timeout=es_timeout,
			index='mrb-proxies',
			doc_type="proxies",
			body={
				"size":100000,
				"sort":[
					{"distance":"asc"}
				],
				"query": {
					"bool" : {
						"filter" : filterData
					}
				}
			})
		#pal = 'AND palindromic = 0'
	else:
		#pal = "AND ( ( pmaf < " + str(maf_threshold) + " AND palindromic = 1 ) OR palindromic = 0)"
		filterData1=[]
		filterData2=[]
		filterData1.append({"term" : {'palindromic':'1'}})
		filterData1.append({"range" : {"pmaf": {"lt": str(maf_threshold) }}})
		filterData2.append({"term" : {'palindromic':'0'}})
		ESRes=es.search(
			request_timeout=es_timeout,
			index='mrb-proxies',
			doc_type="proxies",
			body={
				"size":100000,
				"query": {
					"bool" : {
						"filter" : [
								{"terms" : {'target':snps}},
								{"range" : {"rsq": {"gte": str(rsq) }}},
								{"bool":{
									"should": [
										{"term" : {'palindromic':'0'}},
						                { "bool" : {
						                  "must" : [
						                    {"term" : {'palindromic':'1'}},
											{"range" : {"pmaf": {"lt": str(maf_threshold) }}}
						                  ]
						                }}
									]
								}
							}
						]
					}
				}
			})
		logger2.debug(filterData)
		logger2.debug(filterData1)
		logger2.debug(filterData2)
	#SQL = "SELECT * " \
	#"FROM proxies " \
	#"WHERE target in ({0}) " \
	#"AND rsq >= {1} {2};".format(",".join([ "'" + x + "'" for x in snps ]), rsq, pal)


	#return res
	#logger.info(res)
	logger2.debug("performing proxy query")
	#pquery.Query(SQL)
	#logger2.debug(SQL)
	logger2.debug("done proxy query")
	#res = pquery.record
	proxy_dat = []
	logger2.debug("matching proxy SNPs")
	for i in range(len(snps)):
		snp = snps[i]
		dat = [{'targets':snp, 'proxies': snp, 'tallele1': '', 'tallele2': '', 'pallele1': '', 'pallele2': '', 'pal': ''}]
		hits = ESRes['hits']['hits']
		#logger.info('total proxies = '+str(ESRes['hits']['total']))
		for hit in hits:
			#logger2.debug(hit['_source'])
			if hit['_source']['target'] == snp:
				#logger.info(snp+' '+hit['_source']['proxy'])
				dat.append({
						'targets':snp,
						'proxies':hit['_source']['proxy'],
						'tallele1':hit['_source']['tallele1'],
						'tallele2':hit['_source']['tallele2'],
						'pallele1':hit['_source']['pallele1'],
						'pallele2':hit['_source']['pallele2'],
						'pal':hit['_source']['palindromic']}
				)
		proxy_dat.append(dat)
	logger2.debug("done proxy matching")
	end = time.time()
	t=round((end - start), 4)
	logger2.debug('proxy matching took: '+str(t)+' seconds')
	logger2.debug('returned '+str(len(proxy_dat))+' results')
	return proxy_dat


def extract_proxies_from_query(outcomes, snps, proxy_dat, proxy_query, maf_threshold, align_alleles):
	logger2.debug("entering extract_proxies_from_query")
	start = time.time()
	matched_proxies = []
	proxy_query_copy = [a.get('name') for a in proxy_query]
	for i in range(len(outcomes)):
		logger2.debug("matching proxies to query snps for " + str(i))
		for j in range(len(snps)):
			#logger.info(str(j)+' '+snps[j])
			flag=0
			for k in range(len(proxy_dat[j])):
				#logger.info(str(k)+' '+str(proxy_dat[j][k]))
				if flag == 1:
					#logger.info(flag)
					break
				for l in range(len(proxy_query)):
					if (proxy_query[l].get('name') == proxy_dat[j][k].get('proxies')) and (str(proxy_query[l].get('id')) == outcomes[i]):
						#logger.info(proxy_query[l].get('name'))
						y = dict(proxy_query[l])
						y['target_snp'] = snps[j]
						y['proxy_snp'] = proxy_query[l].get('name')
						#logger.info(y['target_snp']+' : '+y['proxy_snp'])
						if(snps[j] == proxy_query[l].get('name')):
							y['proxy'] = False
							y['target_a1'] = None
							y['target_a2'] = None
							y['proxy_a1'] = None
							y['proxy_a2'] = None
							matched_proxies.append(y.copy())
							flag = 1
						else:
							if align_alleles == "1":
								al = proxy_alleles(proxy_query[l], proxy_dat[j][k], maf_threshold)
								logger2.debug(al)
								if al == "straight":
									y['proxy'] = True
									y['effect_allele'] = proxy_dat[j][k].get('tallele1')
									y['other_allele'] = proxy_dat[j][k].get('tallele2')
									y['target_a1'] = proxy_dat[j][k].get('tallele1')
									y['target_a2'] = proxy_dat[j][k].get('tallele2')
									y['proxy_a1'] = proxy_dat[j][k].get('pallele1')
									y['proxy_a2'] = proxy_dat[j][k].get('pallele2')
									y['name'] = snps[j]
									matched_proxies.append(y.copy())
									flag = 1
									# print "straight", i, j, k, l
									break
								if al == "switch":
									y['proxy'] = True
									y['effect_allele'] = proxy_dat[j][k].get('tallele2')
									y['other_allele'] = proxy_dat[j][k].get('tallele1')
									y['target_a1'] = proxy_dat[j][k].get('tallele1')
									y['target_a2'] = proxy_dat[j][k].get('tallele2')
									y['proxy_a1'] = proxy_dat[j][k].get('pallele1')
									y['proxy_a2'] = proxy_dat[j][k].get('pallele2')
									y['name'] = snps[j]
									matched_proxies.append(y.copy())
									flag = 1
									# print "switch", i, j, k, l
									break
								if al == "skip":
									logger2.debug("skip")
							else:
								y['proxy'] = True
								y['target_a1'] = proxy_dat[j][k].get('tallele1')
								y['target_a2'] = proxy_dat[j][k].get('tallele2')
								y['proxy_a1'] = proxy_dat[j][k].get('pallele1')
								y['proxy_a2'] = proxy_dat[j][k].get('pallele2')
								y['name'] = snps[j]
								matched_proxies.append(dict(y))
								flag = 1
								# print "unaligned", i, j, k, l
								break
	end = time.time()
        t=round((end - start), 4)
        logger2.debug('extract_proxies_from_query took :'+str(t)+' seconds')
	return matched_proxies



def flip(x):
	if x == "A":
		return "T"
	if x == "T":
		return "A"
	if x == "G":
		return "C"
	if x == "C":
		return "G"


def allele_check(x):
	if x is None:
		return x
	x = x.upper()
	if x == "A":
		return x
	if x == "T":
		return x
	if x == "G":
		return x
	if x == "C":
		return x
	return None


def proxy_alleles(pq, pd, maf_threshold):
	mallele1 = allele_check(pq.get('effect_allele'))
	mallele2 = allele_check(pq.get('other_allele'))
	tallele1 = pd.get('tallele1')
	tallele2 = pd.get('tallele2')
	pallele1 = pd.get('pallele1')
	pallele2 = pd.get('pallele2')
	if mallele1 is None:
		return "no allele"
	pal = pd.get('pal')
	eaf = pq.get('effect_allele_freq')
	if pal == "0":
		if (mallele1 == pallele1 and mallele2 == pallele2) or (mallele1 == flip(pallele1) and mallele2 == flip(pallele2)):
			return "straight"
		if (mallele1 == pallele2 and mallele2 == pallele1) or (mallele1 == flip(pallele2) and mallele2 == flip(pallele1)):
			return "switch"
		if (mallele1 == pallele1 and mallele2 == None) or (mallele1 == flip(pallele1) and mallele2 == None):
			return "straight"
		if (mallele1 == pallele2 and mallele2 == None) or (mallele1 == flip(pallele2) and mallele2 == None):
			return "switch"
		return "skip"
	if pal == "1":
		if eaf == None:
			return "skip"
		if eaf < maf_threshold:
			if (mallele1 == pallele1 and mallele2 == pallele2) or (mallele1 == pallele1 and mallele2 == None):
				return "straight"
			if (mallele1 == flip(pallele1) and mallele2 == flip(pallele2)) or (mallele1 == flip(pallele1) and mallele2 == None):
				return "switch"
		if eaf > 1 - maf_threshold:
			if (mallele1 == pallele1 and mallele2 == pallele2) or (mallele1 == pallele1 and mallele2 == None):
				return "switch"
			if (mallele1 == flip(pallele1) and mallele2 == flip(pallele2)) or (mallele1 == flip(pallele1) and mallele2 == None):
				return "straight"
		return "skip"

def study_info(study_list):
	study_data = {}
	#SQL   = "SELECT * FROM study_e where id in ('"+str(",".join(study_list))+"');"
	if study_list == 'snp_lookup':
		SQL = "SELECT * FROM study_e, permissions_e where study_e.id = permissions_e.study_id and permissions_e.gid = 1;"
	else:
		SQL   = "SELECT * FROM study_e where id in ("+study_list+");"

	logger2.debug(SQL)
	query = PySQLPool.getNewQuery(dbConnection)
	query.Query(SQL)
	for q in query.record:
		study_data[q['id']]=q
	#logger2.debug(study_data)
	logger2.debug('study_info:'+str(len(study_data)))
	return study_data

def snp_info(snp_list,type):
	snp_data = {}
	if type == 'id_to_rsid':
		SQL   = "SELECT * FROM snp where id in ("+str(",".join(snp_list))+");"
	else:
		SQL   = "SELECT * FROM snp where name in ("+str(",".join(snp_list))+");"
	#logger2.debug(SQL)
	start=time.time()
	query = PySQLPool.getNewQuery(dbConnection)
	query.Query(SQL)
	for q in query.record:
		snp_data[q['id']]=q['name']
	end = time.time()
	t=round((end - start), 4)
	logger2.debug('snp_info:'+str(len(snp_data))+' in '+str(t)+' seconds')
	return snp_data

def elastic_search(filterData,index_name):
	res=es.search(
		request_timeout=es_timeout,
		index=index_name,
		#doc_type="assoc",
		body={
			#"from":from_val,
			"size":100000,
			"query": {
				"bool" : {
					"filter" : filterData
				}
			}
		})
	return res

#studies and snps are lists
def elastic_query(studies,snps,pval):
	#separate studies by index
	#logger2.debug(studies)
	study_indexes={mrb_batch:[]}
	mrbase_original=True
	#deal with snp_lookup
	if studies == 'snp_lookup':
		logger2.debug("Running snp_lookup elastic_query")
		#need to add each index for snp_lookups
		for i in study_batches:
			if i != mrb_batch and i not in private_batches:
				study_indexes.update({i:[]})
	else:
		for o in studies:
			#logger2.debug('o = '+o)
			if re.search(':',o):
				study_prefix,study_id = o.split(':')
				if study_prefix in study_indexes:
					study_indexes[study_prefix].append(study_id)
				else:
					study_indexes[study_prefix] = [study_id]
			else:
				study_indexes[mrb_batch].append(o)

	res={}
	for s in study_indexes:
		logger2.debug('checking '+s+' ...')
		filterSelect = {}
		if type(studies) is list:
			filterSelect['study_id'] = study_indexes[s]
		if snps != '':
			filterSelect['snp_id'] = snps
		if pval != '':
			filterSelect['p'] = pval

		filterData=[]
		for f in filterSelect:
			if f in ['study_id','snp_id']:
				filterData.append({"terms" : {f:filterSelect[f]}})
			else:
				filterData.append({"range" : {"p": {"lt": filterSelect[f]}}})

		#deal with mrbase-original complications
		run=False
		if s == mrb_batch:
			if studies=='snp_lookup':
				run=True
			elif 'study_id' in filterSelect:
				if len(filterSelect['study_id'])>0:
					run=True
		else:
			run = True
		if run==True:
			logger2.debug('running ES: index: '+s+' studies: '+str(len(studies))+' snps: '+str(len(snps))+' pval: '+str(pval))
			logger2.debug(filterData)
			start=time.time()
			e =  elastic_search(filterData,s)
			res.update({s:e})
			#res.update({'index_name':s})
			end = time.time()
			t=round((end - start), 4)
			numRecords=res[s]['hits']['total']
			logger2.debug("Time taken: "+str(t)+" seconds")
			logger2.debug('ES returned '+str(numRecords)+' records')
	#if numRecords>10000:
	#	for i in range(10000,numRecords,10000):
	#		logger2.debug(i)
	#		res1 = elastic_search(i,10,filterData)
	#		res = merge_two_dicts(res,res1)
	#	logger2.debug(str(numRecords)+' !!!! large number of records !!!!')
	return res

"""

Methods

"""

@app.route("/")
#@cache.cached(timeout=50,key_prefix='hello')
def hello():
	logger2.debug("INCOMING")
	return "Welcome to the MR-Base API. This was automatically deployed."


@app.route("/upload", methods=['GET', 'POST'])
def upload():
        logger.info('upload')
	if request.method == 'POST':
		file = request.files['file']
		if file and allowed_file(file.filename):
			filename = secure_filename(file.filename)
			file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
			return redirect(url_for('upload'))
	return """
	<!doctype html>
	<title>Upload new File</title>
	<h1>Upload new File</h1>
	<form action="" method=post enctype=multipart/form-data>
	  <p><input type=file name=file>
		 <input type=submit value=Upload>
	</form>
	<p>%s</p>
	""" % "<br>".join(os.listdir(app.config['UPLOAD_FOLDER'],))


@app.route("/check_token", methods=[ 'GET' ])
def check_token():
	a = request.args.get('access_token')
	logger2.debug(a)
	if not request.args.get('access_token'):
		return json.dumps(-1)
	if request.args.get('access_token'):
		return json.dumps(check_access_token(request.args.get('access_token')))
	else:
		return json.dumps(-1)


@app.route("/get_studies", methods=[ 'GET' ])
def get_studies():
	logger.info('get_studies')
	logger2.debug("\n\n\nRequesting study table")
	access_query = token_query(request.args.get('access_token'))
	query = PySQLPool.getNewQuery(dbConnection)
	SQL   = "SELECT * FROM study_e c WHERE c.id NOT IN (1000000) AND" + access_query + ";"
	query.Query(SQL)
	return json.dumps(query.record, ensure_ascii=False)


@app.route("/get_effects", methods=[ 'GET' ])
def get_effects():
	logger.info('get_effects')
	if not request.args.get('outcomes') or not request.args.get('snps'):
		return json.dumps([])

	outcomes = joinarg('outcomes')
	snps     = joinarg('snps')
	return json.dumps(query_summary_stats(request.args.get('access_token'), snps, outcomes))

@app.route("/snp_lookup", methods=[ 'GET' ])
#@cache.cached(300, key_prefix='snp-lookup')
def snp_lookup():
	logger.info('snp_lookup')
	if not request.args.get('snps'):
		return json.dumps([])
	snps = joinarg('snps')
	search_type = request.args.get('search_type')
	logger2.debug('search_type = '+search_type)
	data = query_summary_stats(request.args.get('access_token'), snps, 'snp_lookup')
	dataFilt=[]
	if search_type == 'all':
		dataFilt = data
	else:
		logger2.debug('Filtering...')
		for d in data:
			if float(d['p'])<1e-3:
				dataFilt.append(d)
			#logger.info(d)
	logger2.debug(len(dataFilt))
	logger2.debug('Done')
	return json.dumps({'data':dataFilt})


@app.route("/get_status", methods=[ 'GET' ])
def get_status():
	SQL   = "SELECT COUNT(*) FROM study;"
	query = PySQLPool.getNewQuery(dbConnection)
	query.Query(SQL)
	return json.dumps(query.record)




@app.route("/extract_instruments", methods=[ 'GET' ])
def extract_instruments():
	logger.info('extract_instruments')
	if not request.args.get('outcomes'):
		return json.dumps([])

	if not request.args.get('pval'):
		pval = 5e-8
	else:
		pval = float(request.args.get('pval'))
	if not request.args.get('clump'):
		logger2.debug("no clump argument")
		clump = "yes"
	elif request.args.get('clump') == "no" or request.args.get('clump') == "No":
		clump = request.args.get('clump')
	else: clump = "yes"
	if not request.args.get('p1'):
		p1 = pval
	else:
		p1 = float(request.args.get('p1'))
	if not request.args.get('p2'):
		p2 = pval
	else:
		p2 = float(request.args.get('p2'))
	if not request.args.get('r2'):
		r2 = 0.1
	else:
		r2 = float(request.args.get('r2'))
	if not request.args.get('kb'):
		kb = 5000
	else:
		kb = int(request.args.get('kb'))

	if p1 > p2:
		p2 = p1

	outcomes = joinarg('outcomes')

	logger2.debug("obtaining instruments for "+outcomes)
	logger2.debug("clumping = "+clump)

	### elastic query
	#fix outcomes
	outcomes_clean = outcomes.replace("'","")
	#get available studies
	study_access = token_query_list(request.args.get('access_token'))
	#logger2.debug(sorted(study_access))
	logger2.debug('searching '+outcomes_clean)
	outcomes_access = []
	for o in outcomes_clean.split(','):
		if o in study_access:
			outcomes_access.append(o)
		else:
			logger2.debug(o+" not in access_list")
	if len(outcomes_access)==0:
		logger2.debug('No outcomes left after permissions check')
		return json.dumps([], ensure_ascii=False)
	else:
		ESRes = elastic_query(snps='',studies=outcomes_access,pval=pval)
		#logger2.debug(ESRes)
		snpDic={}
		#create lookup for snp names
		for s in ESRes:
			hits = ESRes[s]['hits']['hits']
			for hit in hits:
				snpDic[hit['_source']['snp_id']]=''

		#get study and snp data
		#study_data = study_info([outcomes])[outcomes]
		study_data = study_info(outcomes)
		#snp_data = snp_info(snpDic.keys(),'id_to_rsid')
		snp_data = snpDic.keys()

		#create final file
		numRecords=0
		res=[]
		for s in ESRes:
			hits = ESRes[s]['hits']['hits']
			numRecords+=int(ESRes[s]['hits']['total'])
			for hit in hits:
				other_allele = effect_allele = effect_allele_freq = beta = se = p = n = ''
				if hit['_source']['effect_allele_freq'] < 999:
					effect_allele_freq = hit['_source']['effect_allele_freq']
				if hit['_source']['beta'] < 999:
					#beta = "%4.3f" % float(hit['_source']['beta'])
					beta = hit['_source']['beta']
				if hit['_source']['se'] < 999:
					#se = "%03.02e" % float(hit['_source']['se'])
					se = hit['_source']['se']
				if hit['_source']['p'] < 999:
					#p = "%03.02e" % float(hit['_source']['p'])
					p = hit['_source']['p']
				if 'n' in hit['_source']:
					n = hit['_source']['n']
				if 'effect_allele' in hit['_source']:
					effect_allele = hit['_source']['effect_allele']
				if 'other_allele' in hit['_source']:
					other_allele = hit['_source']['other_allele']
				name = hit['_source']['snp_id']
				#logger2.debug(hit)
				#don't want data with no pval
				if p != '':
					assocDic = {'effect_allele':effect_allele,
						'other_allele':other_allele,
						'effect_allelel_freq':effect_allele_freq,
						'beta':beta,
						'se':se,
						'p':p,
						'n':n,
						'name':name
					}
					study_id = hit['_source']['study_id']
					if s != mrb_batch:
						study_id = s+':'+hit['_source']['study_id']
					#make sure only to return available studies
					if study_id in study_data:
						assocDic.update(study_data[study_id])
						#logger2.debug(assocDic)
						#res.append(study_data)
						res.append(assocDic)
		#es_res.append(study_data)
		#logger2.debug(json.dumps(res[0],indent=4))

		#### mysql

		# access_query = token_query(request.args.get('access_token'))
		# query = PySQLPool.getNewQuery(dbConnection)
		#
		#
		# SQL = "SELECT a.effect_allele, a.other_allele, a.effect_allele_freq, a.beta, a.se, a.p, a.n, b.name, c.* " \
		# 		"FROM assoc a, snp b, study c " \
		# 		"WHERE a.snp=b.id AND a.study=c.id " \
		# 		"AND a.study IN ({0}) " \
		# 		"AND a.p <= {1} " \
		# 		"AND {2}" \
		# 		"ORDER BY a.study;".format(outcomes, pval, access_query)
		# logger2.debug("querying database...")
		# start = time.time()
		# query.Query(SQL)
		# res_mysql = query.record
		# end = time.time()
		# t=round((end - start), 4)
		# logger2.debug(json.dumps(res_mysql[0],indent=4))
		# logger2.debug("mysql done. found "+str(len(res_mysql))+" hits in "+str(t)+" seconds")

		#token = request.args.get('access_token')
		#user_email = get_user_email(token)
		studies = outcomes.strip().split(",")
		nsnps = len(res)

		#if query.affectedRows == 0L:
		#	return json.dumps([])
		if clump =="yes" and numRecords != 0:
			found_outcomes = set([x.get('id') for x in res])
			all_out = []
			for outcome in found_outcomes:
				logger2.debug("clumping results for "+str(outcome))
				ress = [x for x in res if x.get('id') == outcome]
				snps = set([x.get('name') for x in res if x.get('id') == outcome])

				# print "getting position"
				# cp = get_snp_positions(snps)
				# print "got position"

				fn = str(uuid.uuid4())
				# out = plink_clumping(fn, UPLOAD_FOLDER, cp, ress, "name", "p", p1, p2, r2, kb)
				out = plink_clumping_rs(fn, UPLOAD_FOLDER, ress, "name", "p", p1, p2, r2, kb)
				all_out = all_out + out

			return json.dumps(all_out, ensure_ascii=False)

		return json.dumps(res, ensure_ascii=False)


@app.route("/get_effects_from_file", methods=[ 'GET' ])
def get_effects_from_file():
	logger.info('get_effects_from_file')
	logger2.debug("Extracting effects based on file uploads")
	if not request.args.get('outcomefile') or not request.args.get('snpfile'):
		return json.dumps([])
	if not check_filename(request.args.get('outcomefile')) or not check_filename(request.args.get('snpfile')):
		return json.dumps([])
	if not request.args.get('proxies'):
		logger2.debug("not getting proxies by default")
		proxies = '0'
	else:
		proxies = request.args.get('proxies')
	logger2.debug('proxies: '+str(proxies))
	if not request.args.get('rsq'):
		rsq = 0.8
	else:
		rsq = float(request.args.get('rsq'))
	if not request.args.get('align_alleles'):
		align_alleles = '1'
	else:
		align_alleles = request.args.get('align_alleles')
	if not request.args.get('palindromes'):
		palindromes = '1'
	else:
		palindromes = '0'
	if not request.args.get('maf_threshold'):
		maf_threshold = 0.3
	else:
		maf_threshold = float(request.args.get('maf_threshold'))

	snpfile     = UPLOAD_FOLDER + os.path.basename(request.args.get('snpfile'))
	outcomefile = UPLOAD_FOLDER + os.path.basename(request.args.get('outcomefile'))

	with open(snpfile) as f:
		snps = f.readlines()
		snps = [x.strip("\n") for x in snps]
	os.remove(snpfile)

	with open(outcomefile) as f:
		outcomes = f.readlines()
		outcomes = [x.strip("\n") for x in outcomes]
	os.remove(outcomefile)

	logger2.debug("extracting data for "+str(len(snps))+" SNP(s) in "+str(len(outcomes))+" outcome(s)")

	if proxies == '0':
		logger2.debug("not using LD proxies")
		snps = ",".join([ "'" + x.strip("\n") + "'" for x in snps])
		outcomes = ",".join([ "'" + x.strip("\n") + "'" for x in outcomes])
		return json.dumps(query_summary_stats(request.args.get('access_token'), snps, outcomes), ensure_ascii=False)
	else:
		logger2.debug("using LD proxies")
		# cp = get_snp_positions(snps)
		# snps = [x.get('name') for x in cp]
		# chr = [x.get('chrom').replace("chr", "eur") + ".ld" for x in cp]
		proxy_dat = get_proxies_es(snps, rsq, palindromes, maf_threshold)
		#logger.info(proxy_dat)
		#proxy_dat_mysql = get_proxies_mysql(snps, rsq, palindromes, maf_threshold)
		#proxy_dat = get_proxies_mysql(snps, rsq, palindromes, maf_threshold)
		#proxy_dat_mysql = get_proxies_mysql(snps, rsq, palindromes, maf_threshold)

		proxies = [x.get('proxies') for x in [item for sublist in proxy_dat for item in sublist]]
		#proxies_mysql = [x.get('proxies') for x in [item for sublist in proxy_dat_mysql for item in sublist]]
		# proxy_query = query_summary_stats(request.args.get('access_token'), joinarray(proxies), joinarray(outcomes))
		proxy_query = query_summary_stats(request.args.get('access_token'), joinarray(proxies), joinarray(outcomes))
		#logger.info(proxy_query)
		#proxy_query_mysql = query_summary_stats(request.args.get('access_token'), joinarray(proxies_mysql), joinarray(outcomes))
		res=[]
		if proxy_query!='[]':
			res = extract_proxies_from_query(outcomes, snps, proxy_dat, proxy_query, maf_threshold, align_alleles)
			#logger.info('\nmysql')
			#res_mysql = extract_proxies_from_query(outcomes, snps, proxy_dat_mysql, proxy_query_mysql, maf_threshold, align_alleles)
		return json.dumps(res, ensure_ascii=False)


@app.route("/clump", methods=[ 'GET' ])
def clump():
	logger.info('clump')
        if not request.args.get('snpfile'):
		return json.dumps([])
	if not check_filename(request.args.get('snpfile')):
		return json.dumps([])
	if not request.args.get('p1'):
		p1 = 1
	else:
		p1 = int(request.args.get('p1'))
	if not request.args.get('p2'):
		p2 = 1
	else:
		p2 = int(request.args.get('p2'))
	if not request.args.get('r2'):
		r2 = 0.1
	else:
		r2 = float(request.args.get('r2'))
	if not request.args.get('kb'):
		kb = 5000
	else:
		kb = int(request.args.get('kb'))


	fn = os.path.basename(request.args.get('snpfile'))
	snpfile = UPLOAD_FOLDER + fn

	ress = []
	f = open(snpfile, "r")
	reader = csv.DictReader(f, delimiter=" ")
	for row in reader:
		ress.append(row)

	f.close()

	# snps = [x.get('SNP') for x in ress]
	# cp = get_snp_positions(snps)

	# out = plink_clumping(fn, UPLOAD_FOLDER, cp, ress, "SNP", "P", p1, p2, r2, kb)
	out = plink_clumping_rs(fn, UPLOAD_FOLDER, ress, "SNP", "P", p1, p2, r2, kb)
	return json.dumps(out, ensure_ascii=False)

@app.route("/ld", methods=[ 'GET' ])
def ld():
    logger.info('ld')
    if not request.args.get('snpfile'):
        return json.dumps([])
    if not check_filename(request.args.get('snpfile')):
        return json.dumps([])

    fn = os.path.basename(request.args.get('snpfile'))
    snpfile = UPLOAD_FOLDER + fn

    with open(snpfile) as f:
        snps = f.readlines()
        snps = [x.strip("\n") for x in snps]
    os.remove(snpfile)

    out = plink_ldsquare_rs(fn, UPLOAD_FOLDER, snps)
    return json.dumps(out, ensure_ascii=False)


@app.route("/test_api_server", methods=[ 'GET' ])
def test_api_server():
	return "API server alive!!!!??"



if __name__ == "__main__":
	#app.run(host='0.0.0.0', debug=True, port=80)
	app.run(host='0.0.0.0', debug=True, port=8080)
