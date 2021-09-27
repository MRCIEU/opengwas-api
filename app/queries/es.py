import flask
import re
from resources.globals import Globals
import json
import logging
import time
from queries.cql_queries import get_permitted_studies, get_all_gwas_for_user
from queries.variants import parse_chrpos

logger = logging.getLogger('debug-log')
query_logger = logging.getLogger('query-log')

#globals
es_timeout=120
return_size=100000

def make_multi_body_text(filterData,pval=''):
    m = {
        "size":return_size,
        "query": {
            "bool" : {
                "filter" : filterData
                }
            }
        }
    if pval != '':
         m["post_filter"] = {
                "range": {"p": {"lt": pval}}
            }
    return m

def organise_variants(variants):
    rsreg = r'^rs\d+$'
    crreg = r'^\d+:\d+$'
    cpreg = r'^\d+:\d+-\d+$'
    out = {
        'rsid': [x for x in variants if re.match(rsreg, x)],
        'chrpos': parse_chrpos([x for x in variants if re.match(crreg, x)]),
        'cprange': parse_chrpos([x for x in variants if re.match(cpreg, x)])
    }
    return out


def organise_payload(res, index):
    x = [o['_source'] for o in res['hits']['hits']]
    for i in range(len(x)):
        x[i]['id'] = index + '-' + x[i].pop('gwas_id')
        x[i]['rsid'] = x[i].pop('snp_id')
        x[i]['ea'] = x[i].pop('effect_allele')
        x[i]['nea'] = x[i].pop('other_allele')
        x[i]['eaf'] = x[i].pop('effect_allele_freq')
    return x

def organise_payload_multi(hit):
    reg = r'^([\w]+-[\w]+)-([\w]+)'
    x = [o['_source'] for o in hit['hits']['hits']]
    indexes = [o['_index'] for o in hit['hits']['hits']]
    indexes = [x.replace("ukbb", "ukb") for x in indexes]
    for i in range(len(x)):
        study_prefix, study_id = re.match(reg, indexes[i]).groups()
        x[i]['id'] = study_prefix + '-' + x[i].pop('gwas_id')
        x[i]['rsid'] = x[i].pop('snp_id')
        x[i]['ea'] = x[i].pop('effect_allele')
        x[i]['nea'] = x[i].pop('other_allele')
        x[i]['eaf'] = x[i].pop('effect_allele_freq')
    return x

def add_trait_to_result(res, study_data):
    for i in range(len(res)):
        res[i]['trait'] = study_data[res[i]['id']]['trait']
    return res


def get_assoc(user_email, variants, id, proxies, r2, align_alleles, palindromes, maf_threshold):
    variants = organise_variants(variants)
    study_data = get_permitted_studies(user_email, id)
    id_access = list(study_data.keys())
    if len(id_access) == 0:
        return []

    rsid = variants['rsid']
    chrpos = variants['chrpos']
    cprange = variants['cprange']

    allres = []
    if len(rsid) > 0:
        if proxies == 0:
            logger.debug("not using LD proxies")
            try:
                allres += elastic_query_rsid(rsid=rsid, studies=id_access)
            except Exception as e:
                logging.error("Could not obtain summary stats: {}".format(e))
                flask.abort(503, e)
        else:
            logger.debug("using LD proxies")
            try:
                proxy_dat = get_proxies_es(rsid, r2, palindromes, maf_threshold)
                proxies = [x.get('proxies') for x in [item for sublist in proxy_dat for item in sublist]]
                proxy_query = elastic_query_rsid(rsid=proxies, studies=id_access)
                res = []
                # Need to fix this
                if proxy_query != '[]':
                    res = extract_proxies_from_query(id, rsid, proxy_dat, proxy_query, maf_threshold, align_alleles)
                allres += res
            except Exception as e:
                logging.error("Could not obtain summary stats: {}".format(e))
                flask.abort(503, e)

    if len(chrpos) > 0:
        logger.debug("not using LD proxies")
        try:
            res = elastic_query_chrpos(chrpos=chrpos, studies=id_access)
            allres += res
        except Exception as e:
            logging.error("Could not obtain summary stats: {}".format(e))
            flask.abort(503, e)

    if len(cprange) > 0:
        logger.debug("not using LD proxies")
        try:
            res = elastic_query_cprange(cprange=cprange, studies=id_access)
            allres += res
        except Exception as e:
            logging.error("Could not obtain summary stats: {}".format(e))
            flask.abort(503, e)

    allres = add_trait_to_result(allres, study_data)
    return allres


def phewas_elastic_search(filterData, index_name, pval):
    res = Globals.es.search(
        ignore_unavailable=True,
        request_timeout=es_timeout,
        index=index_name,
        # doc_type="assoc",
        body={
            # "from":from_val,
            "size": return_size,
            "query": {
                "bool": {
                    "filter": filterData
                }
            },
            "post_filter": {
                "range": {"p": {"lt": pval}}
            }
        }
    )
    return res

def elastic_search(filterData, index_name):
    res = Globals.es.search(
        ignore_unavailable=True,
        request_timeout=es_timeout,
        index=index_name,
        # doc_type="assoc",
        body={
            # "from":from_val,
            "size": return_size,
            "query": {
                "bool": {
                    "filter": filterData
                }
            },
        })
    return res

def elastic_search_multi(bodyText):
    logger.debug(bodyText)
    print(bodyText)
    res = Globals.es.msearch(
        body=bodyText, request_timeout=es_timeout)
    return res


def match_study_to_index(studies):
    study_indexes = {}
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
    return study_indexes


def elastic_query_phewas_rsid(rsid, user_email, pval, index_list=[]):
    study_indexes = Globals.public_batches
    if len(index_list) > 0:
        study_indexes = [x for x in study_indexes if x in index_list]
    res = []
    request = []
    for s in study_indexes:
        logger.debug('checking ' + s + ' ...')
        req_head = {'index': s, "ignore_unavailable":True}
        filterData = []
        filterData.append({"terms": {'snp_id': rsid}})
        bodyText=make_multi_body_text(filterData,pval)
        request.extend([req_head, bodyText])
    start = time.time()
    e = elastic_search_multi(request)
    for response in e['responses']:
        r = organise_payload_multi(response)
        res+=r
    end = time.time()
    t = round((end - start), 4)
    query_logger.debug("\t".join(['name:phewas_rsid',f'time:{t}',f'hits:{len(res)}',f'rsid:{rsid}',f'pval:{pval}',f'indexes:{study_indexes}',f'es:{request}']))
    logger.debug("Time taken: " + str(t) + " seconds")
    logger.debug('ES returned ' + str(len(res)) + ' records')
    # REMOVE DISALLOWED STUDIES
    foundids = [x['id'] for x in res]
    study_data = get_permitted_studies(user_email, foundids)
    id_access = list(study_data.keys())
    res = [x for x in res if x['id'] in id_access]
    res = add_trait_to_result(res, study_data)
    return res


def elastic_query_phewas_chrpos(chrpos, user_email, pval, index_list=[]):
    study_indexes = Globals.public_batches
    if len(index_list) > 0:
        study_indexes = [x for x in study_indexes if x in index_list]
    res = []
    request = []
    for s in study_indexes:
        if len(chrpos) > 0:
            chrom = list(set([x['chr'] for x in chrpos]))
            for c in chrom:
                pos = [x['start'] for x in chrpos if x['chr'] == c]
                logger.debug('checking ' + s + ' ...')
                filterData = []
                filterData.append({"terms": {'chr': [c]}})
                filterData.append({"terms": {'position': pos}})
                req_head = {'index': s, "ignore_unavailable":True}
                bodyText=make_multi_body_text(filterData,pval)
                request.extend([req_head, bodyText])
    start = time.time()
    e = elastic_search_multi(request)
    for response in e['responses']:
        r = organise_payload_multi(response)
        res+=r
    end = time.time()
    end = time.time()
    t = round((end - start), 4)
    query_logger.debug("\t".join(['name:phewas_chrpos',f'time:{t}',f'hits:{len(res)}',f'chrpos:{chrpos}',f'pval:{pval}',f'indexes:{study_indexes}',f'es:{request}']))
    logger.debug("Time taken: " + str(t) + " seconds")
    logger.debug('ES returned ' + str(len(res)) + ' records')
    # REMOVE DISALLOWED STUDIES
    foundids = [x['id'] for x in res]
    study_data = get_permitted_studies(user_email, foundids)
    id_access = list(study_data.keys())
    res = [x for x in res if x['id'] in id_access]
    res = add_trait_to_result(res, study_data)
    return res


def elastic_query_phewas_cprange(cprange, user_email, pval, index_list=[]):
    study_indexes = Globals.public_batches
    if len(index_list) > 0:
        study_indexes = [x for x in study_indexes if x in index_list]
    res = []
    request = []
    
    for s in study_indexes:
        if len(cprange) > 0:
            for c in cprange:
                logger.debug('checking ' + s + ' ...')
                filterData = []
                filterData.append({"terms": {'chr': [c['chr']]}})
                filterData.append({"range": {'position': {'gte': c['start'], 'lte': c['end']}}})
                req_head = {'index': s, "ignore_unavailable":True}
                bodyText=make_multi_body_text(filterData,pval)
                request.extend([req_head, bodyText])
                #filterData.append({"range": {"p": {"lt": pval}}})
    start = time.time()
    e = elastic_search_multi(request)
    for response in e['responses']:
        r = organise_payload_multi(response)
        res+=r
    end = time.time()
    t = round((end - start), 4)
    query_logger.debug("\t".join(['name:phewas_cprange',f'time:{t}',f'hits:{len(res)}',f'cprange:{cprange}',f'pval:{pval}',f'indexes:{study_indexes}',f'es:{request}']))
    logger.debug("Time taken: " + str(t) + " seconds")
    logger.debug('ES returned ' + str(len(res)) + ' records')
    # REMOVE DISALLOWED STUDIES
    foundids = [x['id'] for x in res]
    study_data = get_permitted_studies(user_email, foundids)
    id_access = list(study_data.keys())
    res = [x for x in res if x['id'] in id_access]
    res = add_trait_to_result(res, study_data)
    return res


def elastic_query_chrpos(studies, chrpos):
    study_indexes = match_study_to_index(studies)
    res = []
    request = []
    for s in study_indexes:
        if len(chrpos) > 0:
            chrom = list(set([x['chr'] for x in chrpos]))
            for c in chrom:
                pos = [x['start'] for x in chrpos if x['chr'] == c]
                logger.debug('checking ' + s + ' ...')
                filterData = []
                filterData.append({"terms": {'gwas_id': study_indexes[s]}})
                filterData.append({"terms": {'chr': [c]}})
                filterData.append({"terms": {'position': pos}})
                req_head = {'index': s, "ignore_unavailable":True}
                bodyText=make_multi_body_text(filterData)
                request.extend([req_head, bodyText])
    start = time.time()
    e = elastic_search_multi(request)
    for response in e['responses']:
        r = organise_payload_multi(response)
        res+=r
    end = time.time()
    t = round((end - start), 4)
    query_logger.debug("\t".join(['name:chrpos',f'time:{t}',f'hits:{len(res)}',f'chrpos:{chrpos}',f'gwas:{studies}',f'indexes:{study_indexes}',f'es:{request}']))
    logger.debug("Time taken: " + str(t) + " seconds")
    logger.debug('ES returned ' + str(len(res)) + ' records')
    return res


def elastic_query_cprange(studies, cprange):
    study_indexes = match_study_to_index(studies)
    res = []
    request = []
    for s in study_indexes:
        if len(cprange) > 0:
            for c in cprange:
                pos1 = [x['start'] for x in cprange]
                pos2 = [x['end'] for x in cprange]
                logger.debug('checking ' + s + ' ...')
                filterData = []
                filterData.append({"terms": {'gwas_id': study_indexes[s]}})
                filterData.append({"terms": {'chr': [c['chr']]}})
                filterData.append({"range": {'position': {'gte': c['start'], 'lte': c['end']}}})
                req_head = {'index': s, "ignore_unavailable":True}
                bodyText=make_multi_body_text(filterData)
                request.extend([req_head, bodyText])
    start = time.time()
    e = elastic_search_multi(request)
    for response in e['responses']:
        r = organise_payload_multi(response)
        res+=r
    end = time.time()
    t = round((end - start), 4)
    query_logger.debug("\t".join(['name:cprange',f'time:{t}',f'hits:{len(res)}',f'cprange:{cprange}',f'gwas{studies}',f'indexes{study_indexes}',f'es:{request}']))
    logger.debug("Time taken: " + str(t) + " seconds")
    logger.debug('ES returned ' + str(len(res)) + ' records')
    return res

def elastic_query_rsid(studies,rsid):
    study_indexes = match_study_to_index(studies)
    res = []
    request = []
    start = time.time()
    for s in study_indexes:
        if len(rsid) > 0:
            logger.debug('checking ' + s + ' ...')
            req_head = {'index': s, "ignore_unavailable":True}
            filterData=[
                    {"terms":{"gwas_id":study_indexes[s]}},
                    {"terms":{"snp_id":rsid}}
                    ]
            bodyText=make_multi_body_text(filterData)
            request.extend([req_head, bodyText])
    e = elastic_search_multi(request)
    for response in e['responses']:
        r = organise_payload_multi(response)
        res+=r
    end = time.time()
    t = round((end - start), 4)
    query_logger.debug("\t".join(['name:rsid',f'time:{t}',f'hits:{len(res)}',f'rsid:{rsid}',f'gwas:{studies}',f'indexes:{study_indexes}',f'es:{request}']))
    logger.debug("Time taken: " + str(t) + " seconds")
    logger.debug('ES returned ' + str(len(res)) + ' records')
    return res

def elastic_query_pval(studies, pval, tophits=False, bychr=False):
    study_indexes = match_study_to_index(studies)
    res = []
    request = []
    start = time.time()
    if bychr:
        for c in Globals.CHROMLIST:
            request = []
            for s in study_indexes:
                filterData = []
                filterData.append({"terms": {'gwas_id': study_indexes[s]}})
                filterData.append({"range": {"p": {"lt": pval}}})
                fd2 = filterData.copy()
                fd2.append({"terms": {"chr": [c]}})
                if tophits:
                    #print("looking in tophits index")
                    s = s + "-tophits"
                req_head = {'index': s, "ignore_unavailable":True}
                bodyText=make_multi_body_text(fd2)
                request.extend([req_head, bodyText])
            e = elastic_search_multi(request)
            for response in e['responses']:
                r = organise_payload_multi(response)
                res+=r
    else:
        for s in study_indexes:
            filterData = []
            filterData.append({"terms": {'gwas_id': study_indexes[s]}})
            filterData.append({"range": {"p": {"lt": pval}}})
            if tophits:
                print("looking in tophits index")
                s = s + "-tophits"
            req_head = {'index': s, "ignore_unavailable":True}
            bodyText=make_multi_body_text(filterData)
            request.extend([req_head, bodyText])
        e = elastic_search_multi(request)
        for response in e['responses']:
            r = organise_payload_multi(response)
            res+=r
    end = time.time()
    t = round((end - start), 4)
    query_logger.debug("\t".join(['name:pval',f'time:{t}',f'hits:{len(res)}',f'pval:{pval}',f'gwas:{studies}',f'indexes:{study_indexes}',f'es:{request}']))
    logger.debug("Time taken: " + str(t) + " seconds")
    logger.debug('ES returned ' + str(len(res)) + ' records')
    return res


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
            request_timeout=es_timeout,
            index='mrb-proxies',
            doc_type="proxies",
            body={
                "size": return_size,
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
            request_timeout=es_timeout,
            index='mrb-proxies',
            doc_type="proxies",
            body={
                "size": return_size,
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


def extract_proxies_from_query(outcomes, snps, proxy_dat, proxy_query, maf_threshold, align_alleles, proxies_only=False):
    logger.debug("entering extract_proxies_from_query")
    start = time.time()
    matched_proxies = []
    proxy_query_copy = [a.get('rsid') for a in proxy_query]
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
                    if (proxy_query[l].get('rsid') == proxy_dat[j][k].get('proxies')) and (
                            str(proxy_query[l].get('id')) == outcomes[i]):
                        # logger.info(proxy_query[l].get('rsid'))
                        y = dict(proxy_query[l])
                        y['target_snp'] = snps[j]
                        y['proxy_snp'] = proxy_query[l].get('rsid')
                        # logger.info(y['target_snp']+' : '+y['proxy_snp'])
                        if (snps[j] == proxy_query[l].get('rsid') and not proxies_only):
                            y['proxy'] = False
                            y['target_a1'] = None
                            y['target_a2'] = None
                            y['proxy_a1'] = None
                            y['proxy_a2'] = None
                            matched_proxies.append(y.copy())
                            flag = 1
                        else:
                            if align_alleles == 1:
                                al = proxy_alleles(proxy_query[l], proxy_dat[j][k], maf_threshold)
                                logger.debug(al)
                                if al == "straight":
                                    y['proxy'] = True
                                    y['ea'] = proxy_dat[j][k].get('tallele1')
                                    y['nea'] = proxy_dat[j][k].get('tallele2')
                                    y['target_a1'] = proxy_dat[j][k].get('tallele1')
                                    y['target_a2'] = proxy_dat[j][k].get('tallele2')
                                    y['proxy_a1'] = proxy_dat[j][k].get('pallele1')
                                    y['proxy_a2'] = proxy_dat[j][k].get('pallele2')
                                    y['rsid'] = snps[j]
                                    matched_proxies.append(y.copy())
                                    flag = 1
                                    logger.debug("straight" + " " + str(i) + " " + str(j) + " " + str(k) + " " + str(l))
                                    break
                                if al == "switch":
                                    y['proxy'] = True
                                    y['ea'] = proxy_dat[j][k].get('tallele2')
                                    y['nea'] = proxy_dat[j][k].get('tallele1')
                                    y['target_a1'] = proxy_dat[j][k].get('tallele1')
                                    y['target_a2'] = proxy_dat[j][k].get('tallele2')
                                    y['proxy_a1'] = proxy_dat[j][k].get('pallele1')
                                    y['proxy_a2'] = proxy_dat[j][k].get('pallele2')
                                    y['rsid'] = snps[j]
                                    matched_proxies.append(y.copy())
                                    flag = 1
                                    logger.debug("switch" + " " + str(i) + " " + str(j) + " " + str(k) + " " + str(l))
                                    break
                                if al == "skip":
                                    logger.debug("skip")
                            else:
                                y['proxy'] = True
                                y['target_a1'] = proxy_dat[j][k].get('tallele1')
                                y['target_a2'] = proxy_dat[j][k].get('tallele2')
                                y['proxy_a1'] = proxy_dat[j][k].get('pallele1')
                                y['proxy_a2'] = proxy_dat[j][k].get('pallele2')
                                y['rsid'] = snps[j]
                                matched_proxies.append(dict(y))
                                flag = 1
                                logger.debug("unaligned" + " " + str(i) + " " + str(j) + " " + str(k) + " " + str(l))
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
    mallele1 = allele_check(pq.get('ea'))
    mallele2 = allele_check(pq.get('nea'))
    tallele1 = pd.get('tallele1')
    tallele2 = pd.get('tallele2')
    pallele1 = pd.get('pallele1')
    pallele2 = pd.get('pallele2')
    if mallele1 is None:
        return "no allele"
    pal = pd.get('pal')
    eaf = pq.get('eaf')
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
        if not eaf:
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
