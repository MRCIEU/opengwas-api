import flask
import re
from resources.globals import Globals
import json
import logging
import time
from queries.cql_queries import get_permitted_studies, get_all_gwas_for_user

logger = logging.getLogger('debug-log')


def get_assoc(user_email, rsid, id, proxies, r2, align_alleles, palindromes, maf_threshold):
    if proxies == 0:
        logger.debug("not using LD proxies")

        try:
            return query_summary_stats(user_email, rsid, id)
        except Exception as e:
            logging.error("Could not obtain summary stats: {}".format(e))
            flask.abort(503, e)

    else:
        logger.debug("using LD proxies")

        try:
            proxy_dat = get_proxies_es(rsid, r2, palindromes, maf_threshold)
            proxies = [x.get('proxies') for x in [item for sublist in proxy_dat for item in sublist]]

            proxy_query = query_summary_stats(user_email, proxies, id)

            res = []

            if proxy_query != '[]':
                res = extract_proxies_from_query(id, rsid, proxy_dat, proxy_query, maf_threshold, align_alleles)

            return res

        except Exception as e:
            logging.error("Could not obtain summary stats: {}".format(e))
            flask.abort(503, e)


def get_proxies_es(snps, rsq, palindromes, maf_threshold):
    logger.debug("obtaining LD proxies from ES")
    logger.debug("palindromes " + str(palindromes))
    start = time.time()
    start = time.time()
    # pquery = PySQLPool.getNewQuery(dbConnection)
    filterData = []
    filterData.append({"terms": {'target': snps}})
    filterData.append({"range": {"rsq": {"gte": str(rsq)}}})
    # logger.info(filterData)
    if palindromes == 0:
        filterData.append({"term": {'palindromic': '0'}})
        ESRes = Globals.es.search(
            request_timeout=120,
            index='mrb-proxies',
            doc_type="proxies",
            body={
                "size": 100000,
                "sort": [
                    {"distance": "asc"}
                ],
                "query": {
                    "bool": {
                        "filter": filterData
                    }
                }
            })
    # pal = 'AND palindromic = 0'
    else:
        # pal = "AND ( ( pmaf < " + str(maf_threshold) + " AND palindromic = 1 ) OR palindromic = 0)"
        filterData1 = []
        filterData2 = []
        filterData1.append({"term": {'palindromic': '1'}})
        filterData1.append({"range": {"pmaf": {"lt": str(maf_threshold)}}})
        filterData2.append({"term": {'palindromic': '0'}})
        ESRes = Globals.es.search(
            request_timeout=120,
            index='mrb-proxies',
            doc_type="proxies",
            body={
                "size": 100000,
                "query": {
                    "bool": {
                        "filter": [
                            {"terms": {'target': snps}},
                            {"range": {"rsq": {"gte": str(rsq)}}},
                            {"bool": {
                                "should": [
                                    {"term": {'palindromic': '0'}},
                                    {"bool": {
                                        "must": [
                                            {"term": {'palindromic': '1'}},
                                            {"range": {"pmaf": {"lt": str(maf_threshold)}}}
                                        ]
                                    }}
                                ]
                            }
                            }
                        ]
                    }
                }
            })
        logger.debug(filterData)
        logger.debug(filterData1)
        logger.debug(filterData2)
    # SQL = "SELECT * " \
    # "FROM proxies " \
    # "WHERE target in ({0}) " \
    # "AND rsq >= {1} {2};".format(",".join([ "'" + x + "'" for x in snps ]), rsq, pal)

    # return res
    # logger.info(res)
    logger.debug("performing proxy query")
    # pquery.Query(SQL)
    # logger.debug(SQL)
    logger.debug("done proxy query")
    # res = pquery.record
    proxy_dat = []
    logger.debug("matching proxy SNPs")
    for i in range(len(snps)):
        snp = snps[i]
        dat = [
            {'targets': snp, 'proxies': snp, 'tallele1': '', 'tallele2': '', 'pallele1': '', 'pallele2': '', 'pal': ''}]
        hits = ESRes['hits']['hits']
        # logger.info('total proxies = '+str(ESRes['hits']['total']))
        for hit in hits:
            # logger.debug(hit['_source'])
            if hit['_source']['target'] == snp:
                # logger.info(snp+' '+hit['_source']['proxy'])
                dat.append({
                    'targets': snp,
                    'proxies': hit['_source']['proxy'],
                    'tallele1': hit['_source']['tallele1'],
                    'tallele2': hit['_source']['tallele2'],
                    'pallele1': hit['_source']['pallele1'],
                    'pallele2': hit['_source']['pallele2'],
                    'pal': hit['_source']['palindromic']}
                )
        proxy_dat.append(dat)
    logger.debug("done proxy matching")
    end = time.time()
    t = round((end - start), 4)
    logger.debug('proxy matching took: ' + str(t) + ' seconds')
    logger.debug('returned ' + str(len(proxy_dat)) + ' results')
    return proxy_dat


def elastic_search(filterData, index_name):
    res = Globals.es.search(
        ignore_unavailable=True,
        request_timeout=120,
        index=index_name,
        # doc_type="assoc",
        body={
            # "from":from_val,
            "size": 100000,
            "query": {
                "bool": {
                    "filter": filterData
                }
            }
        })
    return res


# studies and snps are lists
def elastic_query(studies, snps, pval):
    # separate studies by index
    # logger.debug(studies)
    study_indexes = {}
    mrbase_original = True
    # deal with snp_lookup
    if studies == 'snp_lookup':
        logger.debug("Running snp_lookup elastic_query")
        # need to add each index for snp_lookups
        for i in Globals.study_batches:
            if i not in Globals.private_batches:
                study_indexes.update({i: []})
    else:
        for o in studies:
            # logger.debug('o = '+o)
            if re.search('-', o):
                reg = r'^([\w]+-[\w]+)-([\w]+)'
                study_prefix, study_id = re.match(reg, o).groups()
                if study_prefix in study_indexes:
                    study_indexes[study_prefix].append(study_id)
                else:
                    study_indexes[study_prefix] = [study_id]
            else:
                logger.debug(o+'is not a correct batch prefix')
    res = {}
    for s in study_indexes:
        logger.debug('checking ' + s + ' ...')
        filterSelect = {}
        if type(studies) is list:
            filterSelect['study_id'] = study_indexes[s]
        if snps != '':
            filterSelect['snp_id'] = snps
        if pval != '':
            filterSelect['p'] = pval

        filterData = []
        for f in filterSelect:
            if f in ['study_id', 'snp_id']:
                filterData.append({"terms": {f: filterSelect[f]}})
            else:
                filterData.append({"range": {"p": {"lt": filterSelect[f]}}})

        # deal with mrbase-original complications
        run = False
        if studies == 'snp_lookup':
            run = True
        elif 'study_id' in filterSelect:
            if len(filterSelect['study_id']) > 0:
                run = True
        else:
            run = True
        if run == True:
            logger.debug('running ES: index: ' + s + ' studies: ' + str(len(studies)) + ' snps: ' + str(
                len(snps)) + ' pval: ' + str(pval))
            # logger.debug(filterData)
            start = time.time()
            e = elastic_search(filterData, s)
            res.update({s: e})
            # res.update({'index_name':s})
            end = time.time()
            t = round((end - start), 4)
            numRecords = res[s]['hits']['total']
            logger.debug("Time taken: " + str(t) + " seconds")
            logger.debug('ES returned ' + str(numRecords) + ' records')
    # if numRecords>10000:
    #	for i in range(10000,numRecords,10000):
    #		logger.debug(i)
    #		res1 = elastic_search(i,10,filterData)
    #		res = merge_two_dicts(res,res1)
    #	logger.debug(str(numRecords)+' !!!! large number of records !!!!')
    return res


def query_summary_stats(user_email, snps, outcomes):
    # get available studies
    logger.debug('requested studies: ' + str(len(outcomes)))
    logger.debug('len snplist = ' + str(len(snps)))

    # get study and snp data
    snp_data = snps
    logger.debug('searching ' + str(outcomes.count(',') + 1) + ' outcomes')
    logger.debug('creating outcomes list and study_data dictionary')
    start = time.time()
    outcomes_access = []
    outcomes_clean = ','.join(outcomes)
    if outcomes == 'snp_lookup':
        outcomes_access = 'snp_lookup'
        study_data = get_all_gwas_for_user(user_email)
    else:
        study_data = get_permitted_studies(user_email, outcomes)
        outcomes_access = list(study_data.keys())
    end = time.time()
    t = round((end - start), 4)
    logger.debug('took: ' + str(t) + ' seconds')
    logger.debug('len study_data = ' + str(len(study_data)))
    logger.debug('len outcomes_access = ' + str(len(outcomes_access)))
    if len(outcomes_access) == 0 and outcomes != 'snp_lookup':
        return json.dumps([])
    ESRes = elastic_query(snps=snp_data, studies=outcomes_access, pval='')
    logger.debug('ES queries finished')
    es_res = []
    logger.debug(len(ESRes))
    for s in ESRes:
        logger.debug(s)
        hits = ESRes[s]['hits']['hits']

        # create final file

        for hit in hits:
            # logger.debug(hit)
            other_allele = effect_allele = effect_allele_freq = beta = se = p = n = ''
            # if float(hit['_source']['effect_allele_freq']) < 999:
            effect_allele_freq = hit['_source']['effect_allele_freq']
            # if hit['_source']['beta'] < 999:
            # beta = "%4.3f" % float(hit['_source']['beta'])
            beta = hit['_source']['beta']
            # if hit['_source']['se'] < 999:
            # se = "%03.02e" % float(hit['_source']['se'])
            se = hit['_source']['se']
            # if hit['_source']['p'] < 999:
            # p = "%03.02e" % float(hit['_source']['p'])
            p = hit['_source']['p']
            # if 'n' in hit['_source']:
            n = hit['_source']['n']
            # if 'effect_allele' in hit['_source']:
            effect_allele = hit['_source']['effect_allele']
            # if 'other_allele' in hit['_source']:
            other_allele = hit['_source']['other_allele']
            # name = snp_data[int(hit['_source']['snp_id'])]
            name = hit['_source']['snp_id']
            # logger.debug(hit)
            # don't want data with no pval
            if p != '':
                assocDic = {'effect_allele': effect_allele,
                            'other_allele': other_allele,
                            'effect_allele_freq': effect_allele_freq,
                            'beta': beta,
                            'se': se,
                            'p': p,
                            'n': n,
                            'name': name
                            }
                #study_id = hit['_source']['study_id']
                study_id = s + '-' + hit['_source']['study_id']
                # make sure only to return available studies
                outcomes_access = list(study_data.keys())
                if study_id in study_data:
                    assocDic.update(study_data[study_id])
                    es_res.append(assocDic)

    # logger.debug(json.dumps(es_res,indent=4))
    logger.debug('Total hits returned = ' + str(len(es_res)))
    return es_res


# logger.debug(json.dumps(es_res[0],indent=4))

def extract_proxies_from_query(outcomes, snps, proxy_dat, proxy_query, maf_threshold, align_alleles):
    logger.debug("entering extract_proxies_from_query")
    start = time.time()
    matched_proxies = []
    proxy_query_copy = [a.get('name') for a in proxy_query]
    for i in range(len(outcomes)):
        logger.debug("matching proxies to query snps for " + str(outcomes[i]))
        for j in range(len(snps)):
            # logger.info(str(j)+' '+snps[j])
            flag = 0
            for k in range(len(proxy_dat[j])):
                # logger.info(str(k)+' '+str(proxy_dat[j][k]))
                if flag == 1:
                    # logger.info(flag)
                    break
                for l in range(len(proxy_query)):
                    if (proxy_query[l].get('name') == proxy_dat[j][k].get('proxies')) and (
                            str(proxy_query[l].get('id')) == outcomes[i]):
                        # logger.info(proxy_query[l].get('name'))
                        y = dict(proxy_query[l])
                        y['target_snp'] = snps[j]
                        y['proxy_snp'] = proxy_query[l].get('name')
                        # logger.info(y['target_snp']+' : '+y['proxy_snp'])
                        if (snps[j] == proxy_query[l].get('name')):
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
                                logger.debug(al)
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
                                    logger.debug("skip")
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
    t = round((end - start), 4)
    logger.debug('extract_proxies_from_query took :' + str(t) + ' seconds')
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
        if (mallele1 == pallele1 and mallele2 == pallele2) or (
                mallele1 == flip(pallele1) and mallele2 == flip(pallele2)):
            return "straight"
        if (mallele1 == pallele2 and mallele2 == pallele1) or (
                mallele1 == flip(pallele2) and mallele2 == flip(pallele1)):
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
            if (mallele1 == flip(pallele1) and mallele2 == flip(pallele2)) or (
                    mallele1 == flip(pallele1) and mallele2 == None):
                return "switch"
        if eaf > 1 - maf_threshold:
            if (mallele1 == pallele1 and mallele2 == pallele2) or (mallele1 == pallele1 and mallele2 == None):
                return "switch"
            if (mallele1 == flip(pallele1) and mallele2 == flip(pallele2)) or (
                    mallele1 == flip(pallele1) and mallele2 == None):
                return "straight"
        return "skip"
