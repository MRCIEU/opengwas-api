def elastic_search(filterData,index_name):
	res=es.search(
		request_timeout=60,
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
			if i != mrb_batch:
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
			#logger2.debug(filterData)
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


#create list of studies available to user
def token_query_list(token):
	qList = []
	user_email = get_user_email(token)
	logger2.debug("getting credentials for "+user_email)
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
	# logger2.debug(SQL)
	query = PySQLPool.getNewQuery(dbConnection)
	query.Query(SQL)
	for q  in query.record:
		qList.append(q['id'])
	logger2.debug('access to '+str(len(qList))+' studies')
	return qList



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
