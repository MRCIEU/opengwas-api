import datetime

from flask_restx import Resource, Namespace
import logging
import json

from middleware.auth import key_required
from queries.cql_queries import *
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
