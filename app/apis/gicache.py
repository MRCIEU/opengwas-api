from flask_restx import Resource, Namespace
import logging
import json

from middleware.auth import jwt_required
from queries.cql_queries import *
from resources.globals import Globals


logger = logging.getLogger('debug-log')

api = Namespace('gicache', description="Manually update the gwasinfo cache")


@api.route('')
@api.doc(description="Update cache for default public GWAS info and update stats for all batches")
class Info(Resource):
    parser = api.parser()

    @api.expect(parser)
    @api.doc(id='gicache_get')
    @jwt_required
    def get(self):
        n = save_gwasinfo_cache()
        batches = update_batches_stats()
        return {
            'n_gwasinfo': n,
            'batches': batches
        }


def save_gwasinfo_cache():
    g = get_all_gwas_for_user(None)
    with open(Globals.STATIC_GWASINFO, 'w') as f:
        json.dump(g, f)
    return len(g)
