import requests
import json
import time
import random
import PySQLPool
from multiprocessing import Pool
import multiprocessing


example_get_effects='get_effects?access_token=null&outcomes=1,2,5,6,7,8,9,10,11,12&snps=rs999721,rs9821650,rs9821657,rs1919329,rs6444035,rs3957240,rs1919324,rs2739330'

mrbase_url = 'http://api.mrbase.org/'
mrbase_test_url = 'http://api.mrbase.org/'
crashdown_url = 'http://crashdown.epi.bris.ac.uk:8080/'
crashdown2_url = 'http://crashdown.epi.bris.ac.uk:8090/'
local_url = 'http://localhost:8080/'
cluster_url = 'http://ieu-db-interface.epi.bris.ac.uk:8080/'
oracle_url = 'http://ieu-db-interface.epi.bris.ac.uk:8090/'
#urls = [mrbase_url,crashdown_url]
urls = [cluster_url,oracle_url]
#urls = [mrbase_url,local_url,crashdown_url]

#mysql
#CENTRAL_DB = "./conf_files/central.json"
CENTRAL_DB = "./conf_files/mysql.json"
with open(CENTRAL_DB) as f:
	mrbase_config = json.load(f)
dbConnection = PySQLPool.getNewConnection(**mrbase_config)


def create_random_list(min,max,num):
	r = random.sample(range(min,max),num)
	return r

def create_random_studies(num):
	study_list = []
	#SQL   = "SELECT id FROM study_e ORDER BY RAND() LIMIT "+str(num)+";"
	#SQL   = "SELECT id FROM study_e where id NOT LIKE '%UKB%' ORDER BY RAND() LIMIT "+str(num)+";"
	SQL   = "SELECT id FROM study_e where id LIKE '%ukb-b%' ORDER BY RAND() LIMIT "+str(num)+";"
	print SQL
	#logging.info(SQL)
	start=time.time()
	query = PySQLPool.getNewQuery(dbConnection)
	query.Query(SQL)
	for q in query.record:
		study_list.append(q['id'])
	end = time.time()
	t=round((end - start), 4)
	print 'Getting study_info:'+str(len(study_list))+' in '+str(t)+' seconds'
	return study_list

def create_random_rsids_mysql(num):
	rsid_list = []
	snp_ids = random.sample(range(1,10000000),num)
	snp_ids = ','.join(str(x) for x in snp_ids)
	SQL   = "SELECT * FROM snp where id in ("+snp_ids+");"
	#logging.info(SQL)
	start=time.time()
	query = PySQLPool.getNewQuery(dbConnection)
	query.Query(SQL)
	for q in query.record:
		rsid_list.append(q['name'])
	end = time.time()
	t=round((end - start), 4)
	print 'Getting snp_info:'+str(len(rsid_list))+' in '+str(t)+' seconds'
	return rsid_list

def create_random_rsids(num):
	start=time.time()
	snp_ids = random.sample(range(1,10000000),num)
	rsid_list = ['rs'+str(s) for s in snp_ids]
	end = time.time()
	t=round((end - start), 4)
	print 'Getting snp_info:'+str(len(rsid_list))+' in '+str(t)+' seconds'
	print rsid_list
	return rsid_list

def run_query(url):
	#print url
	start = time.time()
	res = requests.get(url)
	end = time.time()
	t=round((end - start), 4)
	print 'took: '+str(t)+' seconds'
	#print 'res.text len = '+str(len(res.text))
	if len(res.text)>1:
		j = json.loads(res.text)
	else:
		j=''
	#print j
	print '# results = '+str(len(j))
	return t

def get_effects_query():
	base='get_effects?access_token=api_test&outcomes='
	end='&snps='
	outcomes=create_random_studies(1)
	outcomes_string=','.join(str(x) for x in outcomes)
	#print outcomes
	snps=create_random_rsids(10)
	snps_string=','.join(str(x) for x in snps)
	url = base+str(outcomes_string)+end+snps_string
	print str(len(outcomes))+" outcomes "+str(len(snps))+" snps"
	return url

def extract_instruments_query():
	base='extract_instruments?access_token=api_test&outcomes='
	end='&clump=no&pval=1e-8'
	outcomes=create_random_studies(1)
	#print outcomes
	outcomes_string=','.join(str(x) for x in outcomes)
	url = base+str(outcomes_string)+end
	return url

def phewas_query():
	base='snp_lookup?access_token=null&search_type=aaa&snps='
	snps=create_random_rsids(1)
	snps_string=','.join(str(x) for x in snps)
	url = base+str(snps_string)
	return url

def test_apis():
	#get_effects
	print "\n### get_effects ###"
	q1=get_effects_query()
	for u in urls:
		print "\nRunning "+u+" ..."
		url = u+q1
		print url
		run_query(url)
		run_query(url)
		run_query(url)
		run_query(url)

	#extract_instruments
	print "\n### extract_instruments ###"
	q2 = extract_instruments_query()
	for u in urls:
		print "\nRunning "+u+" ..."
		url = u+q2
		print url
		run_query(url)
		run_query(url)
		run_query(url)
		run_query(url)

	#extract_instruments
	print "\n### phewas ###"
	q2 = phewas_query()
	for u in urls:
		print "\nRunning "+u+" ..."
		url = u+q2
		print url
		run_query(url)
		run_query(url)
		run_query(url)
		run_query(url)

def compare_dbs():
	compareList=[]
	for i in range(100):
		print '\n#### '+str(i)+' ####'
		q1=get_effects_query()
		crashdown=crashdown_url+q1
		t1=run_query(crashdown)
		cluster=cluster_url+q1
		t2=run_query(cluster)
		compare=t1/t2
		compareList.append(compare)
		print 'compare = '+str(compare)
	print '\n',reduce(lambda x, y: x + y, compareList) / len(compareList)
	o=open('compare_data.tsv','w')
	count=1
	for c in compareList:
		o.write(str(count)+'\t'+str(c)+'\n')
		count+=1

def db_test():
	snp_list = []
	with open('/Users/be15516/projects/mr-base-elastic/monocyte.clumped.instruments.finalrevised.csv') as f:
		next(f)
		for line in f:
			rs = line.split(',')[0]
			snp_list.append(rs)
	print len(snp_list)
	base='get_effects?access_token=api_test&outcomes='
	end='&snps='
	outcomes_string='1'
	#print outcomes
	snp_list = snp_list[0:10]
	print len(snp_list)
	print snp_list
	snps=','.join(str(x) for x in snp_list)
	url = base+str(outcomes_string)+end+snps
	print len(crashdown_url+url)
	print crashdown_url+url
	run_query(crashdown_url+url)

def test_permissions():
	eList=[33,830,997,998,1013,1082,994,995,277,278,279,280,281,282,283,284,285,286,287,288,289,290,291,1098,978,979,984,985,986,987,988,989,1113,1114,1115,1116,1117,1118,1119,3,3]
	for e in eList:
		print e
		base='extract_instruments?access_token=api_test&outcomes='
		end='&clump=yes&pval=1e-8'
		#outcomes=create_random_studies(e)
		#print outcomes
		#outcomes_string=','.join(str(x) for x in outcomes)
		url = crashdown_url+base+str(e)+end
		print url
		run_query(url)

def stress_test():
	q1=get_effects_query()
	cluster=cluster_url+q1
	processes = [ ]
	time=[]

	threadNum=10
	pool = multiprocessing.Pool(processes = threadNum)
	o=pool.map(run_query, [cluster]*threadNum)
	print(o)
	#for i in range(2):
	#    t = multiprocessing.Process(target=run_query, args=(cluster,retr))
	#    processes.append(t)
	#    t.start()

	#for one_process in processes:
	#    one_process.join()


if __name__ == "__main__":
	test_apis()
	#compare_dbs()
	#db_test()
	#test_permissions()
	#stress_test()
