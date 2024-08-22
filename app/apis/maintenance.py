import datetime

from flask_restx import Resource, Namespace
import logging
import json

from middleware.auth import key_required
from queries.cql_queries import *
from resources.airflow import Airflow
from resources.globals import Globals
from resources.oci import OCI


logger = logging.getLogger('debug-log')

api = Namespace('maintenance', description="Collection of maintenance endpoints")


def save_gwasinfo_cache():
    datasets = get_all_gwas_for_user(None)
    with open(Globals.STATIC_GWASINFO, 'w') as f:
        json.dump({
            'metadata': {
                'updated_at': datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H:%M:%S %Z'),
                'size': len(datasets)
            },
            'datasets': datasets
        }, f)
    with open(Globals.STATIC_GWASINFO, 'rb') as f:
        oci_upload = OCI().object_storage_upload('data', 'gwasinfo.json', f)
    return len(datasets)


@api.route('/make_gwasinfo_cache')
@api.doc(description="Update cache for default public GWAS info and update stats for all batches")
class Info(Resource):
    parser = api.parser()

    @api.expect(parser)
    @api.doc(id='maintenance_make_gwasinfo_cache_get')
    @key_required
    def get(self):
        n = save_gwasinfo_cache()
        batches = update_batches_stats()
        return {
            'n_gwasinfo': n,
            'batches': batches
        }


@api.route('/refresh_added_by_status')
@api.doc(description="Pull update ADDED_BY state for all datasets")
class Info(Resource):
    parser = api.parser()

    @api.expect(parser)
    @api.doc(id='maintenance_refresh_added_by_status_get')
    @key_required
    def get(self):
        gwas_id_and_state = get_added_by_state_of_all_draft_gwas()

        airflow = Airflow()

        for gwas_id, state in gwas_id_and_state.items():
            if state == 1 and airflow.get_dag_run('qc', gwas_id, True)['end_date'] != '':
                set_added_by_state_of_any_gwas(gwas_id, 2)
                gwas_id_and_state[gwas_id] = 2
            elif state == 4 and airflow.get_dag_run('release', gwas_id, True)['end_date'] != '':
                set_added_by_state_of_any_gwas(gwas_id, None)
                del gwas_id_and_state[gwas_id]

        return {
            'gwas_id_and_state': gwas_id_and_state
        }
