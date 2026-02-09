import logging
import time
import mygene

from queries.mysql_queries import MySQLQueries
from resources.globals import Globals

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
    return res['hits']['total']['value'],res['hits']['hits']


# def snps(snp_list):
#     print('snps',len(snp_list))
#     filterData=[
#             {"terms":{"_id":snp_list}},
#             ]
#     total,hits=es_search(filterData=filterData,routing='')
#     return total,hits


# def chrpos_query(chrpos):
#     chrs = list(set([x['chr'] for x in chrpos]))
#     total=0
#     hits=list()
#     for chr in chrs:
#         filterData=[
#                 {"term":{"CHR":chr}},
#                 # {"term":{"COMMON":"1"}},
#                 {"terms" : {"POS": [x['start'] for x in chrpos if x['chr'] == chr]}},
#                 ]
#         tot,hit=es_search(filterData=filterData,routing=chr)
#         total+=tot
#         if tot > 0:
#             for item in hit:
#                 item.update({'query': str(item['_source']['CHR'])+":"+str(item['_source']['POS'])})
#                 so = item['_source']
#                 item.pop('_source')
#                 item.update(so)
#             hits.append(hit)
#     return {"total": total, "results": hits}


def parse_chrpos(chrpos, radius=0):
    out = list()
    chrpos2 = [list(map(str, x.split(':'))) for x in chrpos]
    for i in range(len(chrpos)):
        temp = chrpos2[i][1].split("-")
        if len(temp) == 2:
            out.append({"chr": chrpos2[i][0].replace("chr", ""), "start": max(0, int(temp[0])-radius),"end": int(temp[1])+radius, "type": 'range', 'orig': chrpos[i]})
        elif len(temp) == 1:
            out.append({"chr": chrpos2[i][0].replace("chr", ""), "start": max(0, int(temp[0])-radius), "end": int(temp[0])+radius, "type": 'position', 'orig': chrpos[i]})
        else:
            raise Exception('Malformed chrpos')
    return out


# def range_query(chrpos, radius=0):
#     chrpos = parse_chrpos(chrpos, radius)
#     if radius == 0 and all(x['type'] == 'position' for x in chrpos):
#         return chrpos_query(chrpos)['results']
#
#     out = list()
#
#     for i in range(len(chrpos)):
#         filterData = [
#                 {"term": {"CHR": chrpos[i]['chr']}},
#                 # {"term": {"COMMON": "1"}},
#                 {"range": {"POS": {"gte": chrpos[i]['start'], "lte": chrpos[i]['end']}}},
#                 ]
#         total, hits = es_search(filterData=filterData, routing=chrpos[i]['chr'])
#         if total > 0:
#             for item in hits:
#                 item.update({'query': chrpos[i]['orig']})
#                 so = item['_source']
#                 item.pop('_source')
#                 item.update(so)
#             out.append(hits)
#     return out


# def gene_query(name,radius):
#     mg = mygene.MyGeneInfo()
#     m = mg.getgene(name,'name,symbol,genomic_pos_hg19')
#     if not m:
#         print('No match')
#         return 0, 0
#     if isinstance(m, list):
#         for i in range(len(m)):
#             if 'genomic_pos_hg19' in m[i]:
#                 m = m[i]
#                 break
#     if isinstance(m['genomic_pos_hg19'], dict):
#         pos = m['genomic_pos_hg19']
#     else:  # list (e.g. name=ENSG00000111684, more than one cpranges)
#         # https://github.com/MRCIEU/opengwas-api/issues/16
#         pos = m['genomic_pos_hg19'][0]
#         for p in m['genomic_pos_hg19'][1:]:
#             if len(p['chr']) < len(pos['chr']):
#                 pos = p
#     chr = pos['chr']
#     start = int(pos['start'])
#     end = int(pos['end'])
#     min = 0
#     if start - radius > 0:
#         min = start - radius
#     max = end + radius
#     filterData = [
#         {"term":{"CHR":chr}},
#         # {"term":{"COMMON":"1"}},
#         {"range" : {"POS" : {"gte" : min, "lte" : max}}},
#     ]
#     total, hits = es_search(filterData=filterData, routing=chr)
#     if total > 0:
#         for item in hits:
#             item['dbSNPBuildID'] = item.pop('_index')
#             item['ID'] = item.pop('_id')
#             item.pop('_type')
#             item.pop('_score')
#             item.update({'query': name})
#             so = item['_source']
#             item.pop('_source')
#             item.update(so)
#             item['CHROM'] = item.pop('CHR')
#     return total,hits


def range_query(chrpos: list, radius: int):
    chrpos_raw = chrpos  # Return as the 'query' field
    chrpos = parse_chrpos(chrpos, radius)

    mysql_queries = MySQLQueries()

    result = []

    for i in range(len(chrpos)):
        cp = chrpos[i]

        snps = MySQLQueries().get_snps_by_chrpos({
            int(mysql_queries._encode_chr(cp['chr'])): [(cp['start'], cp['end'])]
        })

        for s in snps:
            result.append({
                'query': chrpos_raw[i],
                'dbSNPBuildID': mysql_queries.dbsnp_build,
                'ID': s['rsid'],
                'CHROM': mysql_queries._decode_chr(s['chr_id']),
                'POS': s['pos'],
            })

    return result


def gene_query(name, radius):
    m = mygene.MyGeneInfo().getgene(name, 'name,symbol,genomic_pos_hg19')
    if not m:
        return []
    if isinstance(m, list):
        for i in range(len(m)):
            if 'genomic_pos_hg19' in m[i]:
                m = m[i]
                break
    if isinstance(m['genomic_pos_hg19'], dict):
        cprange = m['genomic_pos_hg19']
    else:  # list (e.g. name=ENSG00000111684, more than one cpranges)
        # https://github.com/MRCIEU/opengwas-api/issues/16
        cprange = m['genomic_pos_hg19'][0]
        for cpr_candidate in m['genomic_pos_hg19'][1:]:
            if len(cpr_candidate['chr']) < len(cprange['chr']):
                cprange = cpr_candidate

    result = range_query([f"{cprange['chr']}:{cprange['start']}-{cprange['end']}"],radius)

    for r in result:
        r['query'] = name

    return result
