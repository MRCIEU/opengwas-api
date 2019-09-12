import flask
import re
from resources.globals import Globals
import json
import logging
import time
import mygene

logger = logging.getLogger('debug-log')


def es_search(filterData,routing):
	#catch queries that don't require chromosome specific searches
	if routing=='':
		routing = ",".join(map(str, range(1,25)))

	start=time.time()
	res=Globals.es.search(
		request_timeout=60,
		index=Globals.variant_index,
		routing=routing,
		body={
			#"profile":True,
			"size":100000,
			"query": {
				"bool" : {
					"filter" : filterData
				}
			}
		})
	end = time.time()
	t=round((end - start), 4)
	print("Time taken:",t, "seconds")
	return res['hits']['total'],res['hits']['hits']

def snps(snp_list):
	print('snps',len(snp_list))
	filterData=[
			{"terms":{"ID":snp_list}},
			]
	total,hits=es_search(filterData=filterData,routing='')
	return total,hits


def chrpos_query(chrpos):
	chrpos2 = [list(map(int, x.split(':'))) for x in chrpos]
	chrs = list(set([x[0] for x in chrpos2]))


	out = list()
	total=0
	hits=list()

	for chr in chrs:
		filterData=[
				{"term":{"CHROM":chr}},
				{"term":{"COMMON":"1"}},
				{"terms" : {"POS": [x[1] for x in chrpos2 if x[0] == chr]}},
				]
		tot,hit=es_search(filterData=filterData,routing=chr)
		total+=tot
		if tot > 0:
			for item in hit:
				print(item['_source']['POS'])
				item.update({'query': str(item['_source']['CHROM'])+":"+str(item['_source']['POS'])})
				so = item['_source']
				item.pop('_source')
				item.update(so)
			hits.append(hit)
	return {"total":total, "results":hits}

def range_query(chrpos,radius=0):

	if radius == 0:
		return chrpos_query(chrpos)['results']

	chrpos2 = [list(map(int, x.split(':'))) for x in chrpos]
	out = list()

	# def minmax(pos, radius):
	# 	min = 0
	# 	if pos - radius > 0:
	# 		min = pos - radius
	# 	max=pos + radius
	# 	return list(min, max)

	# chrpos3 = [x[0] + minmax(x[1], radius) for x in chrpos2]

	for i in range(len(chrpos)):
		min=0
		if chrpos2[i][1]-radius>0:
			min=chrpos2[i][1]-radius
		max=chrpos2[i][1]+radius
		filterData=[
				{"term":{"CHROM":chrpos2[i][0]}},
				{"term":{"COMMON":"1"}},
				{"range" : {"POS" : {"gte" : min, "lte" : max}}},
				]
		total,hits=es_search(filterData=filterData,routing=chrpos2[i][0])
		print(hits)
		if total > 0:
			for item in hits:
				item.update({'query': chrpos[i]})
				so = item['_source']
				item.pop('_source')
				item.update(so)
			out.append(hits)
	return out

def gene_query(name,radius):
	mg = mygene.MyGeneInfo()
	m = mg.getgene(name,'name,symbol,genomic_pos,genomic_pos_hg19')
	if m:
		chr = m['genomic_pos_hg19']['chr']
		start = int(m['genomic_pos']['start'])
		end = int(m['genomic_pos']['end'])
		min=0
		if start-radius>0:
			min=start-radius
		max=end+radius
		filterData=[
				{"term":{"CHROM":chr}},
				{"term":{"COMMON":"1"}},
				{"range" : {"POS" : {"gte" : min, "lte" : max}}},
				]
		total,hits=es_search(filterData=filterData,routing=chr)
		if total > 0:
			for item in hits:
				item.update({'query': name})
				so = item['_source']
				item.pop('_source')
				item.update(so)
	else:
		print('No match')
		return 0,0
	return total,hits

