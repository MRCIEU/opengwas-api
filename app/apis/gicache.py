from flask_restplus import Resource, Namespace
from flask import request
from queries.cql_queries import *
from schemas.gwas_info_node_schema import GwasInfoNodeSchema
from werkzeug.exceptions import BadRequest
from resources.auth import get_user_email
import logging
import json
from resources.globals import Globals

logger = logging.getLogger('debug-log')

api = Namespace('gicache', description="Manually update the gwasinfo cache")
gwas_info_model = api.model('GwasInfo', GwasInfoNodeSchema.get_flask_model())


@api.route('')
@api.doc(description="Update cache for default public GWAS info")
class Info(Resource):
    parser = api.parser()
    parser.add_argument(
        'X-Api-Token', location='headers', required=False, default='null',
        help=Globals.AUTHTEXT)

    @api.expect(parser)
    @api.doc(model=gwas_info_model)
    def get(self):
        n = save_gwasinfo_cache()
        return {'nrecords': n}


def save_gwasinfo_cache():
    g = get_all_gwas_for_user(None)
    with open(Globals.STATIC_GWASINFO, 'w') as f:
        json.dump(g, f)
    return len(g)
