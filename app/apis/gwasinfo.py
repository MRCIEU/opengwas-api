from flask_restplus import Resource, reqparse, Namespace, fields
from resources._logger import *
from queries.cql_queries import *
from schemas.gwas_info_node_schema import GwasInfoNodeSchema
from queries.gwas_info_node import GwasInfo
from werkzeug.datastructures import FileStorage
import marshmallow.exceptions
from werkzeug.exceptions import BadRequest
from resources._globals import UPLOAD_FOLDER
import hashlib
import gzip
from schemas.gwas_row_schema import GwasRowSchema
import json
import shutil

api = Namespace('gwasinfo', description="Get information about available GWAS summary datasets")
gwas_info_model = api.model('GwasInfo', GwasInfoNodeSchema.get_flask_model())


@api.route('/list')
@api.doc(description="Return all available GWAS summary datasets")
class List(Resource):
    parser = api.parser()
    parser.add_argument(
        'X-Api-Token', location='headers', required=False, default='null',
        help='Public datasets can be queried without any authentication, but some studies are only accessible by specific users. To authenticate we use Google OAuth2.0 access tokens. The easiest way to obtain an access token is through the [TwoSampleMR R](https://mrcieu.github.io/TwoSampleMR/#authentication) package using the `get_mrbase_access_token()` function.')

    @api.expect(parser)
    @api.doc(model=gwas_info_model)
    def get(self):
        logger_info()
        user_email = get_user_email(request.headers.get('X-Api-Token'))
        return get_all_gwas_for_user(user_email)


@api.route('')
@api.doc(description="Get metadata about specified GWAS summary datasets")
class Info(Resource):
    parser = api.parser()
    parser.add_argument(
        'X-Api-Token', location='headers', required=False, default='null',
        help='Public datasets can be queried without any authentication, but some studies are only accessible by specific users. To authenticate we use Google OAuth2.0 access tokens. The easiest way to obtain an access token is through the [TwoSampleMR R](https://mrcieu.github.io/TwoSampleMR/#authentication) package using the `get_mrbase_access_token()` function.')

    @api.expect(parser)
    @api.doc(model=gwas_info_model)
    def get(self):
        logger_info()
        user_email = get_user_email(request.headers.get('X-Api-Token'))
        return get_all_gwas_for_user(user_email)

    parser.add_argument('id', required=False, type=str, action='append', default=[], help="List of IDs")

    @api.expect(parser)
    @api.doc(model=gwas_info_model)
    def post(self):
        logger_info()
        args = self.parser.parse_args()
        user_email = get_user_email(request.headers.get('X-Api-Token'))

        if 'id' not in args or args['id'] is None or len(args['id']) == 0:
            return get_all_gwas_for_user(user_email)
        else:
            recs = []
            for gwas_info_id in args['id']:
                try:
                    recs.append(get_gwas_for_user(user_email, str(gwas_info_id)))
                except LookupError as e:
                    logging.warning("Could not locate study: {}".format(e))
                    continue
            return recs


@api.route('/<gwas_info_id>')
@api.doc(description="Get metadata about specified GWAS summary datasets")
class GetId(Resource):
    parser = api.parser()
    parser.add_argument(
        'X-Api-Token', location='headers', required=False, default='null',
        help='Public datasets can be queried without any authentication, but some studies are only accessible by specific users. To authenticate we use Google OAuth2.0 access tokens. The easiest way to obtain an access token is through the [TwoSampleMR R](https://mrcieu.github.io/TwoSampleMR/#authentication) package using the `get_mrbase_access_token()` function.')

    @api.expect(parser)
    @api.doc(model=gwas_info_model)
    def get(self, gwas_info_id):
        logger_info()
        user_email = get_user_email(request.headers.get('X-Api-Token'))

        try:
            recs = []
            for uid in gwas_info_id.split(','):
                try:
                    recs.append(get_gwas_for_user(user_email, str(uid)))
                except LookupError:
                    continue
            return recs
        except LookupError:
            raise BadRequest("Gwas ID {} does not exist or you do not have permission to view.".format(gwas_info_id))

