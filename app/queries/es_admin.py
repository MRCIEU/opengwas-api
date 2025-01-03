from resources.globals import Globals


logs_index_prefix_api = "og-logs-api-uuid-"
gwas_id_size = 100000  # Should be larger than the number of datasets
user_size = 100000  # Should be larger than the number of users
max_int = 2147483647
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
        request_timeout=120,
        index=_get_index_by_year_month(year, month),
        body={
            "size": 0,
            "aggs": {
                "n_uuid_per_gwas_id": {
                    "terms": {
                        "field": "gwas_id",
                        "order": {
                            "group_by_uuid": "desc"
                        },
                        "size": gwas_id_size
                    },
                    "aggs": {
                        "group_by_uuid": {
                            "cardinality": {
                                "field": "uuid"
                            }
                        }
                    }
                }
            }
        }
    )
    return res['aggregations']['n_uuid_per_gwas_id']['buckets']


def get_most_active_users(year, month):
    res = Globals.es.search(
        request_timeout=120,
        index=_get_index_by_year_month(year, month),
        body={
            "size": 0,
            "runtime_mappings": {
                "n_datasets": {
                    "type": "double",
                    "script": "emit(doc['gwas_id'].size())"
                }
            },
            "aggs": {
                "uuids": {
                    "terms": {
                        "field": "uuid",
                        "size": user_size
                    },
                    "aggs": {
                        "sum_of_time": {
                            "sum": {
                                "field": "time"
                            }
                        },
                        "stats_n_datasets": {
                            "stats": {
                                "field": "n_datasets"
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
    return res['aggregations']['uuids']['buckets']


def get_geoip_using_pipeline(ips):
    result = {}
    body = []

    for ip in ips:
        body.append({"index": {"_index": geoip_converter_index}})
        body.append({"ip": ip})

    Globals.es.bulk(
        request_timeout=120,
        index=geoip_converter_index,
        pipeline="geoip",
        refresh="wait_for",
        body=body
    )

    geoip = Globals.es.search(
        index=geoip_converter_index,
        body={
            "size": max_int,
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
