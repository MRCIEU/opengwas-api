import flask
import re
from resources.globals import Globals
import json
import logging
import time
import mygene

logger = logging.getLogger('debug-log')


def es_search(filterData,routing):
    # catch queries that don't require chromosome specific searches
    if routing == '':
        routing = ",".join(map(str, range(1,25)))

    start = time.time()
    res = Globals.es.search(
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
    chrs = list(set([x['chr'] for x in chrpos]))
    out = list()
    total=0
    hits=list()
    for chr in chrs:
        filterData=[
                {"term":{"CHROM":chr}},
                {"term":{"COMMON":"1"}},
                {"terms" : {"POS": [x['start'] for x in chrpos if x['chr'] == chr]}},
                ]
        tot,hit=es_search(filterData=filterData,routing=chr)
        total+=tot
        if tot > 0:
            for item in hit:
                item.update({'query': str(item['_source']['CHROM'])+":"+str(item['_source']['POS'])})
                so = item['_source']
                item.pop('_source')
                item.update(so)
            hits.append(hit)
    return {"total": total, "results": hits}


def parse_chrpos(chrpos, radius=0):
    out = list()
    chrpos2 = [list(map(str, x.split(':'))) for x in chrpos]
    for i in range(len(chrpos)):
        temp = chrpos2[i][1].split("-")
        if len(temp) == 2:
            out.append({"chr": int(chrpos2[i][0].replace("chr", "")), "start": max(0, int(temp[0])-radius),"end": int(temp[1])+radius, "type": 'range', 'orig': chrpos[i]})
        elif len(temp) == 1:
            out.append({"chr": int(chrpos2[i][0].replace("chr", "")), "start": max(0, int(temp[0])-radius), "end": int(temp[0])+radius, "type": 'position', 'orig': chrpos[i]})
        else:
            raise Exception('Malformed chrpos')
    return out


def range_query(chrpos, radius=0):

    chrpos = parse_chrpos(chrpos, radius)
    if radius == 0 and all(x['type'] == 'position' for x in chrpos):
        return chrpos_query(chrpos)['results']

    out = list()

    for i in range(len(chrpos)):
        filterData = [
                {"term": {"CHROM": chrpos[i]['chr']}},
                {"term": {"COMMON": "1"}},
                {"range": {"POS": {"gte": chrpos[i]['start'], "lte": chrpos[i]['end']}}},
                ]
        total, hits = es_search(filterData=filterData, routing=chrpos[i]['chr'])
        if total > 0:
            for item in hits:
                item.update({'query': chrpos[i]['orig']})
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

