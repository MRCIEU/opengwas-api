from resources.globals import Globals


logs_index_prefix_api = "og-logs-api-"
gwas_id_size = 100000  # Should be larger than the number of datasets
geoip_converter_index = "og-logs-geoip-converter"


def _get_index_by_year_month(year, month):
    index = "{}{}".format(logs_index_prefix_api, str(year))
    if year == "*":
        return index
    elif month == "*":
        return index + ".*"
    return index + "." + str(month).rjust(2, '0')


def get_most_valued_datasets(year, month):
    res = Globals.es.search(
        request_timeout=60,
        index=_get_index_by_year_month(year, month),
        body={
            "size": 0,
            "aggs": {
                "n_uid_per_gwas_id": {
                    "terms": {
                        "field": "gwas_id",
                        "order": {
                            "group_by_uid": "desc"
                        },
                        "size": gwas_id_size
                    },
                    "aggs": {
                        "group_by_uid": {
                            "cardinality": {
                                "field": "uid"
                            }
                        }
                    }
                }
            }
        }
    )
    return res['aggregations']['n_uid_per_gwas_id']['buckets'][:50]


def get_most_active_users(year, month):
    res = Globals.es.search(
        request_timeout=60,
        index=_get_index_by_year_month(year, month),
        body={
            "size": 0,
            "aggs": {
                "uids": {
                    "terms": {
                        "field": "uid",
                        "size": 10000
                    },
                    "aggs": {
                        "sum_of_time": {
                            "sum": {
                                "field": "time"
                            }
                        },
                        "last_record": {
                            "top_hits": {
                                "size": 1,
                                "sort": [{
                                    "@timestamp": {"order": "desc"}
                                }]
                            }
                        }
                    }
                }
            }
        }
    )
    return res['aggregations']['uids']['buckets'][:50]


def get_geoip_using_pipeline(ips):
    result = {}
    body = []

    for ip in ips:
        body.append({"index": {"_index": geoip_converter_index}})
        body.append({"ip": ip})

    Globals.es.bulk(
        request_timeout=60,
        index=geoip_converter_index,
        pipeline="geoip",
        refresh="wait_for",
        body=body
    )

    geoip = Globals.es.search(
        index=geoip_converter_index,
        body={
            "size": 100,
            "query": {
                "terms": {
                    "ip": ips
                }
            }
        }
    )

    for doc in geoip['hits']['hits']:
        if 'geoip' in doc['_source']:
            result[doc['_source']['ip']] = doc['_source']['geoip'].get('country_name', '(?)')
        else:
            result[doc['_source']['ip']] = '(?)'

    Globals.es.delete_by_query(
        index=geoip_converter_index,
        body={
            "query": {
                "match_all": {}
            }
        }
    )

    return result
