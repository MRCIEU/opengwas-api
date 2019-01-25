from flask_restplus import Resource, reqparse, Namespace, fields
from resources._logger import *
from queries.cql_queries import *
from schemas.gwas_info_node_schema import GwasInfoNodeSchema
from schemas.user_node_schema import UserNodeSchema
from schemas.added_by_rel_schema import AddedByRelSchema
from queries.user_node import User
from queries.gwas_info_node import GwasInfo
from queries.added_by_rel import AddedByRel
from werkzeug.datastructures import FileStorage
import time
import marshmallow.exceptions
from werkzeug.exceptions import BadRequest

api = Namespace('gwasinfo', description="Get information about available GWAS summary datasets")

params = GwasInfoNodeSchema.get_flask_model()
params['comments'] = fields.String
model = api.model('gwasinfo', params)

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


parser3 = api.parser()
parser3.add_argument(
    'X-Api-Token', location='headers', required=True,
    help='You must be authenticated to submit new GWAS data. To authenticate we use Google OAuth2.0 access tokens. The easiest way to obtain an access token is through the [TwoSampleMR R](https://mrcieu.github.io/TwoSampleMR/#authentication) package using the `get_mrbase_access_token()` function.')


@api.route('/add')
@api.expect(parser3)
@api.doc(description="Add new gwas information")
class GwasInfoAdd(Resource):
    study_schema = GwasInfoNodeSchema()
    user_schema = UserNodeSchema()
    added_rel = AddedByRelSchema()

    @api.expect(model, validate=False)
    def post(self):
        logger_info()

        try:
            # TODO ? race condition
            req = request.get_json()
            req['id'] = GwasInfo.get_next_numeric_id()

            # load
            user = User(self.user_schema.load({"uid": get_user_email(request.headers.get('X-Api-Token'))}))
            gwasinfo = GwasInfo(self.study_schema.load(req))

            try:
                props = self.added_rel.load({'epoch': time.time(), "comments": req['comments']})
            except KeyError:
                props = self.added_rel.load({'epoch': time.time()})

            # persist or update
            user.create_node()
            gwasinfo.create_node()

            # link study to user; record epoch and optional comments
            rel = AddedByRel(**props)
            rel.create_rel(gwasinfo, user)

            return {"id": gwasinfo['id']}, 200

        except marshmallow.exceptions.ValidationError as e:
            raise BadRequest("Could not validate payload: {}".format(e))


parser3.add_argument('gwas_info_identifier', type=str, required=True,
                     help="Identifier to which the summary stats belong.")
parser3.add_argument('file', location='files', type=FileStorage, required=True,
                     help="Path to GWAS summary stats text file for upload.")
parser3.add_argument('sep', type=str, required=True, default='\t', help="Column separator for file")
parser3.add_argument('skip_rows', type=int, required=True, help="Number of header lines to skip")

parser3.add_argument('chr_idx', type=int, required=False, help="Column index for chromosome (0-indexed)")
parser3.add_argument('pos_idx', type=int, required=False, help="Column index for base position (0-indexed)")
parser3.add_argument('ea_idx', type=int, required=True, help="Column index for effect allele (0-indexed)")
parser3.add_argument('nea_idx', type=int, required=True, help="Column index for non-effect allele (0-indexed)")
parser3.add_argument('dbsnp_idx', type=int, required=False, help="Column index for rs identifer (0-indexed)")
parser3.add_argument('ea_af_idx', type=int, required=False, help="Column index for effect allele frequency (0-indexed)")
parser3.add_argument('effect_idx', type=int, required=True, help="Column index for effect size (0-indexed)")
parser3.add_argument('se_idx', type=int, required=True, help="Column index for standard error (0-indexed)")
parser3.add_argument('pval_idx', type=int, required=True, help="Column index for P-value (0-indexed)")
parser3.add_argument('size_idx', type=int, required=False, help="Column index for study sample size (0-indexed)")
parser3.add_argument('cases_idx', type=int, required=False,
                     help="Column index for number of cases (if case-control study); 0-indexed)")


@api.route('/upload', methods=["post"])
@api.doc(description="Upload GWAS summary stats file")
class UploadGwasSummaryStatsResource(Resource):

    @api.expect(parser3)
    def post(self):
        args = parser3.parse_args()
        uploaded_file = args['file']

        # read file
        contents = uploaded_file.read()
        print(contents)

        # TODO validate file
        # TODO save file in triage

        return {'message': 'Upload successful'}, 201
