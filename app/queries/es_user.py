from resources.globals import Globals


surveys_index = "og-surveys"


def save_survey(es_id, response):
    res = Globals.es.update(
        request_timeout=60,
        index=surveys_index,
        id=es_id,
        doc=response,
        doc_as_upsert=True
    )
    return res


def get_survey_responses(uuid):
    res = Globals.es.search(
        request_timeout=120,
        index=surveys_index,
        body={
            "sort": [
                {
                    "@timestamp": {
                        "order": "desc"
                    }
                }
            ],
            "query": {
                "term": {
                    "uuid": {
                        "value": uuid
                    }
                }
            }
        }
    )
    return res['hits']['hits']
