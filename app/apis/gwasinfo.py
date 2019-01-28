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
        return get_all_gwas(user_email)


@api.route('/')
@api.doc(description="Get metadata about specified GWAS summary datasets")
class InfoPost(Resource):
    parser = api.parser()
    parser.add_argument(
        'X-Api-Token', location='headers', required=False, default='null',
        help='Public datasets can be queried without any authentication, but some studies are only accessible by specific users. To authenticate we use Google OAuth2.0 access tokens. The easiest way to obtain an access token is through the [TwoSampleMR R](https://mrcieu.github.io/TwoSampleMR/#authentication) package using the `get_mrbase_access_token()` function.')

    parser.add_argument('id', required=True, type=str, action='append', default=[], help="List of IDs")

    @api.expect(parser)
    @api.doc(model=gwas_info_model)
    def post(self):
        logger_info()
        args = self.parser.parse_args()
        user_email = get_user_email(request.headers.get('X-Api-Token'))

        if (len(args['id']) == 0):
            return get_all_gwas(user_email)
        else:
            recs = []
            for gwas_info_id in args['id']:
                try:
                    recs.append(get_specific_gwas(user_email, gwas_info_id))
                except LookupError as e:
                    continue
            return recs


@api.route('/add')
@api.doc(description="Add new gwas metadata")
class Add(Resource):
    parser = api.parser()
    parser.add_argument(
        'X-Api-Token', location='headers', required=True,
        help='You must be authenticated to submit new GWAS data. To authenticate we use Google OAuth2.0 access tokens. The easiest way to obtain an access token is through the [TwoSampleMR R](https://mrcieu.github.io/TwoSampleMR/#authentication) package using the `get_mrbase_access_token()` function.')
    GwasInfoNodeSchema.populate_parser(parser, ignore={GwasInfo.get_uid_key()})

    study_schema = GwasInfoNodeSchema()
    user_schema = UserNodeSchema()
    added_rel = AddedByRelSchema()

    @api.expect(parser)
    def post(self):
        logger_info()

        try:
            req = self.parser.parse_args()
            req['id'] = str(GwasInfo.get_next_numeric_id())
            req.pop('X-Api-Token')

            # load
            user = User(self.user_schema.load({"uid": get_user_email(request.headers.get('X-Api-Token'))}))
            gwasinfo = GwasInfo(self.study_schema.load(req))

            # persist or update
            user.create_node()
            gwasinfo.create_node()

            # link study to user; record epoch and optional comments
            rel = AddedByRel(epoch=time.time())
            rel.create_rel(gwasinfo, user)

            return {"id": gwasinfo['id']}, 200

        except marshmallow.exceptions.ValidationError as e:
            raise BadRequest("Could not validate payload: {}".format(e))


@api.route('/delete')
@api.doc(description="Delete gwas metadata")
class Delete(Resource):
    parser = api.parser()
    parser.add_argument(
        'X-Api-Token', location='headers', required=True,
        help='You must be authenticated to delete GWAS data. To authenticate we use Google OAuth2.0 access tokens. The easiest way to obtain an access token is through the [TwoSampleMR R](https://mrcieu.github.io/TwoSampleMR/#authentication) package using the `get_mrbase_access_token()` function.')
    parser.add_argument('id', type=str, required=True,
                        help="Identifier to which the summary stats belong.")

    user_schema = UserNodeSchema()

    @api.expect(parser)
    def delete(self):
        logger_info()
        args = self.parser.parse_args()

        try:
            # check token resolves to valid email
            User(self.user_schema.load({"uid": get_user_email(request.headers.get('X-Api-Token'))}))

            # delete gwasinfo node and connecting rels
            GwasInfo.delete_node(args['id'])
        except marshmallow.exceptions.ValidationError as e:
            raise BadRequest("Could not validate payload: {}".format(e))


@api.route('/upload')
@api.doc(description="Upload GWAS summary stats file")
class Upload(Resource):
    parser = api.parser()
    parser.add_argument(
        'X-Api-Token', location='headers', required=True,
        help='You must be authenticated to submit new GWAS data. To authenticate we use Google OAuth2.0 access tokens. The easiest way to obtain an access token is through the [TwoSampleMR R](https://mrcieu.github.io/TwoSampleMR/#authentication) package using the `get_mrbase_access_token()` function.')
    parser.add_argument('id', type=str, required=True,
                        help="Identifier to which the summary stats belong.")
    parser.add_argument('file', location='files', type=FileStorage, required=True,
                        help="Path to GWAS summary stats text file for upload.")
    parser.add_argument('sep', type=str, required=True, default='\t', help="Column separator for file")
    parser.add_argument('skip_rows', type=int, required=True, help="Number of header lines to skip")

    parser.add_argument('chr_idx', type=int, required=False, help="Column index for chromosome (0-indexed)")
    parser.add_argument('pos_idx', type=int, required=False, help="Column index for base position (0-indexed)")
    parser.add_argument('ea_idx', type=int, required=True, help="Column index for effect allele (0-indexed)")
    parser.add_argument('nea_idx', type=int, required=True, help="Column index for non-effect allele (0-indexed)")
    parser.add_argument('dbsnp_idx', type=int, required=False, help="Column index for rs identifer (0-indexed)")
    parser.add_argument('ea_af_idx', type=int, required=False,
                        help="Column index for effect allele frequency (0-indexed)")
    parser.add_argument('effect_idx', type=int, required=True, help="Column index for effect size (0-indexed)")
    parser.add_argument('se_idx', type=int, required=True, help="Column index for standard error (0-indexed)")
    parser.add_argument('pval_idx', type=int, required=True, help="Column index for P-value (0-indexed)")
    parser.add_argument('size_idx', type=int, required=False, help="Column index for study sample size (0-indexed)")
    parser.add_argument('cases_idx', type=int, required=False,
                        help="Column index for number of cases (if case-control study); 0-indexed)")

    @api.expect(parser)
    def post(self):
        logger_info()
        args = self.parser.parse_args()
        uploaded_file = args['file']

        # read file
        contents = uploaded_file.read()
        print(contents)

        # TODO validate file
        # TODO save file in triage

        return {'message': 'Upload successful'}, 201
