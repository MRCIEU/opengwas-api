from flask_restplus import Resource, reqparse, Namespace
from resources._logger import *
from queries.cql_queries import *

api = Namespace('gwasinfo', description="Get information about available GWAS summary datasets")

parser1 = api.parser()
parser1.add_argument(
    'X-Api-Token', location='headers', required=False, default='null',
    help='Public datasets can be queried without any authentication, but some studies are only accessible by specific users. To authenticate we use Google OAuth2.0 access tokens. The easiest way to obtain an access token is through the [TwoSampleMR R](https://mrcieu.github.io/TwoSampleMR/#authentication) package using the `get_mrbase_access_token()` function.')


@api.route('/list')
@api.expect(parser1)
@api.doc(description="Return all available GWAS summary datasets")
class GwasList(Resource):
    def get(self):
        logger_info()
        user_email = get_user_email(request.headers.get('X-Api-Token'))
        return get_all_gwas(user_email)


@api.route('/<id>')
@api.expect(parser1)
@api.doc(
    description="Get information about specified GWAS summary datasets",
    params={'id': 'An ID or comma-separated list of IDs'}
)
class GwasInfoGet(Resource):
    def get(self, id):
        logger_info()
        user_email = get_user_email(request.headers.get('X-Api-Token'))
        study_ids = id.replace(';', '').split(',')
        recs = []

        for sid in study_ids:
            try:
                recs.append(get_specific_gwas(user_email, sid))
            except LookupError as e:
                continue

        return recs


parser2 = reqparse.RequestParser()
parser2.add_argument('id', required=True, type=str, action='append', default=[], help="List of IDs")
parser2.add_argument(
    'X-Api-Token', location='headers', required=False, default='null',
    help='Public datasets can be queried without any authentication, but some studies are only accessible by specific users. To authenticate we use Google OAuth2.0 access tokens. The easiest way to obtain an access token is through the [TwoSampleMR R](https://mrcieu.github.io/TwoSampleMR/#authentication) package using the `get_mrbase_access_token()` function.')


@api.route('/', methods=["post"])
@api.doc(
    description="Get information about specified GWAS summary datasets")
class GwasInfoPost(Resource):
    @api.expect(parser2)
    def post(self):
        logger_info()
        args = parser2.parse_args()
        user_email = get_user_email(request.headers.get('X-Api-Token'))

        if (len(args['id']) == 0):
            # TODO @Gib reqparse will not allow no args provided shall we remove?
            return get_all_gwas(user_email)
        else:
            recs = []
            for sid in args['id']:
                try:
                    recs.append(get_specific_gwas(user_email, sid))
                except LookupError as e:
                    continue
            return recs
