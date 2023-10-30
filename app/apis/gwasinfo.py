from flask_restplus import Resource, Namespace
from flask import request, send_file
from middleware.auth import jwt_required
from queries.cql_queries import *
from schemas.gwas_info_node_schema import GwasInfoNodeSchema
from werkzeug.exceptions import BadRequest
from resources.auth import get_user_email
import logging
from resources.globals import Globals
import os
import requests

logger = logging.getLogger('debug-log')

api = Namespace('gwasinfo', description="Get information about available GWAS summary datasets")
gwas_info_model = api.model('GwasInfo', GwasInfoNodeSchema.get_flask_model())


@api.route('')
@api.doc(description="Get metadata about specified GWAS summary datasets")
class Info(Resource):
    parser = api.parser()
    parser.add_argument(
        'X-Api-Token', location='headers', required=False, default='null',
        help=Globals.AUTHTEXT)

    @api.expect(parser)
    @api.doc(model=gwas_info_model, id='get_gwas')
    def get(self):
        try:
            user_email = get_user_email(request.headers.get('X-Api-Token'))
            if user_email is None and os.path.exists(Globals.STATIC_GWASINFO):
                # with open(Globals.STATIC_GWASINFO, "r") as f:
                #     a = json.load(f)
                # return a
                return send_file(Globals.STATIC_GWASINFO)
            else:
                return get_all_gwas_for_user(user_email)
        except requests.exceptions.HTTPError as e:
            raise BadRequest("Could not authenticate: {}".format(e))

    parser.add_argument('id', required=False, type=str, action='append', default=[], help="List of GWAS IDs")

    @api.expect(parser)
    @api.doc(model=gwas_info_model, id='get_gwas_post')
    def post(self):
        args = self.parser.parse_args()

        try:
            user_email = get_user_email(request.headers.get('X-Api-Token'))

            if 'id' not in args or args['id'] is None or len(args['id']) == 0:
                return get_all_gwas_for_user(user_email)
            else:
                recs = []
                for gwas_info_id in args['id']:
                    try:
                        recs.append(get_gwas_for_user(user_email, str(gwas_info_id)))
                    except LookupError as e:
                        logger.warning("Could not locate study: {}".format(e))
                        continue
                return recs
        except requests.exceptions.HTTPError as e:
            raise BadRequest("Could not authenticate: {}".format(e))


@api.route('/<id>')
@api.doc(description="Get metadata about specified GWAS summary datasets")
class GetId(Resource):
    parser = api.parser()
    parser.add_argument(
        'X-Api-Token', location='headers', required=False, default='null',
        help=Globals.AUTHTEXT)

    @api.expect(parser)
    # @jwt_required()
    @api.doc(model=gwas_info_model, id='get_gwas_by_id')
    # @jwt_required()
    def get(self, id):

        try:
            token = request.headers.get('X-Api-Token')
            user_email = get_user_email(token)
            recs = []
            for uid in id.split(','):
                try:
                    recs.append(get_gwas_for_user(user_email, str(uid)))
                except LookupError:
                    continue
            return recs
        except LookupError:
            raise BadRequest("Gwas ID {} does not exist or you do not have permission to view.".format(id))
        except requests.exceptions.HTTPError as e:
            raise BadRequest("Could not authenticate: {}".format(e))
