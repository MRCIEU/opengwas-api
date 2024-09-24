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
