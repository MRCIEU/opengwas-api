from flask import request, send_file, g
from flask_restx import Resource, Namespace
from werkzeug.exceptions import BadRequest
import logging
import os

from middleware.auth import jwt_required
from middleware.limiter import limiter, get_allowance_by_user_source, get_key_func_uid
from queries.cql_queries import *
from resources.globals import Globals
from schemas.gwas_info_node_schema import GwasInfoNodeSchema

logger = logging.getLogger('debug-log')

api = Namespace('gwasinfo', description="Get information about available GWAS summary datasets")
gwas_info_model = api.model('GwasInfo', GwasInfoNodeSchema.get_flask_model())


def _get_cost(ids=None):
    if ids is None:
        ids = request.values.getlist('id')
    if not ids or len(ids) > 100:
        return 50
    return 1


@api.route('')
@api.doc(description="Get metadata about specified GWAS summary datasets (or all datasets if no id is specified)")
class Info(Resource):
    parser = api.parser()

    @api.expect(parser)
    @api.doc(model=gwas_info_model, id='get_gwas')
    @jwt_required
    @limiter.shared_limit(limit_value=get_allowance_by_user_source, scope='allowance_by_user_source', key_func=get_key_func_uid, cost=50)
    def get(self):
        # if g.user['uid'] is None and os.path.exists(Globals.STATIC_GWASINFO):
        #     return send_file(Globals.STATIC_GWASINFO)
        return get_all_gwas_for_user(g.user['uid'])

    parser.add_argument('id', required=False, type=str, action='append', default=[], help="List of GWAS IDs")

    @api.expect(parser)
    @api.doc(model=gwas_info_model, id='get_gwas_post')
    @jwt_required
    @limiter.shared_limit(limit_value=get_allowance_by_user_source, scope='allowance_by_user_source', key_func=get_key_func_uid,
                          cost=_get_cost)
    def post(self):
        args = self.parser.parse_args()

        if 'id' not in args or args['id'] is None or len(args['id']) == 0:
            return get_all_gwas_for_user(g.user['uid'])

        recs = []
        for gwas_info_id in args['id']:
            try:
                recs.append(get_gwas_for_user(g.user['uid'], str(gwas_info_id)))
            except LookupError as e:
                logger.warning("Could not locate study: {}".format(e))
                continue
        return recs


@api.route('/<id>')
@api.doc(description="Get metadata about specified GWAS summary datasets")
class GetById(Resource):
    parser = api.parser()

    @api.expect(parser)
    @api.doc(model=gwas_info_model, id='get_gwas_by_id')
    @jwt_required
    def get(self, id):
        ids = id.split(',')

        with limiter.shared_limit(limit_value=get_allowance_by_user_source, scope='allowance_by_user_source', key_func=get_key_func_uid,
                                  cost=lambda: _get_cost(ids)):
            pass

        try:
            recs = []
            for gwas_info_id in ids:
                try:
                    recs.append(get_gwas_for_user(g.user['uid'], str(gwas_info_id)))
                except LookupError:
                    continue
            return recs
        except LookupError:
            raise BadRequest("Gwas ID {} does not exist or you do not have permission to view.".format(id))
