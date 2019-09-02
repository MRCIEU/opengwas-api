import flask
import re
from resources.globals import Globals
import json
import logging
import time

logger = logging.getLogger('debug-log')


def es_search(filterData,routing):
	#catch queries that don't require chromosome specific searches
	if routing=='':
		routing = ",".join(map(str, range(1,25)))
	print(filterData,'routing:',routing)

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

def range_query(chr,pos,radius=0):
	print(type(chr))
	print(type(pos))
	print(type(radius))
	min=0
	if pos-radius>0:
		min=pos-radius
	max=pos+radius
	filterData=[
			{"term":{"CHROM":chr}},
			{"term":{"COMMON":"1"}},
			{"range" : {"POS" : {"gte" : min, "lte" : max}}},
			]
	print(filterData)
	total,hits=es_search(filterData=filterData,routing=chr)
	return total,hits

def gene(name,distance):
	logger.info("gene {} {}",name, distance, feature="f-strings")
	mg = mygene.MyGeneInfo()
	m = mg.getgene(name,'name,symbol,genomic_pos,genomic_pos_hg19')
	if m:
		print(m)
		chr = m['genomic_pos_hg19']['chr']
		start = int(m['genomic_pos']['start'])
		end = int(m['genomic_pos']['end'])
		min=0
		if start-distance>0:
			min=start-distance
		max=end+distance
		filterData=[
				{"term":{"CHROM":chr}},
				{"term":{"COMMON":"1"}},
				{"range" : {"POS" : {"gte" : min, "lte" : max}}},
				]
		total,hits=es_search(filterData=filterData,routing=chr)
	else:
		print('No match')
		return 0,0
	return total,hits

