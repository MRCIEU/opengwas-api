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
                except LookupError:
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


@api.route('/add')
@api.doc(description="Add new gwas metadata")
class Add(Resource):
    parser = api.parser()
    parser.add_argument(
        'X-Api-Token', location='headers', required=True,
        help='You must be authenticated to submit new GWAS data. To authenticate we use Google OAuth2.0 access tokens. The easiest way to obtain an access token is through the [TwoSampleMR R](https://mrcieu.github.io/TwoSampleMR/#authentication) package using the `get_mrbase_access_token()` function.')
    parser.add_argument('gid', type=int, required=True, help='Identifier for the group this study should belong to.')
    GwasInfoNodeSchema.populate_parser(parser, ignore={GwasInfo.get_uid_key(), 'filename', 'path'})

    @api.expect(parser)
    def post(self):
        logger_info()

        try:
            req = self.parser.parse_args()
            user_uid = get_user_email(request.headers.get('X-Api-Token'))
            group_uid = req['gid']

            req.pop('X-Api-Token')
            req.pop('gid')

            gwas_uid = add_new_gwas(user_uid, req, group_uid)

            return {"id": gwas_uid}, 200

        except marshmallow.exceptions.ValidationError as e:
            raise BadRequest("Could not validate payload: {}".format(e))


@api.route('/delete')
@api.doc(description="Delete gwas metadata")
class Delete(Resource):
    parser = api.parser()
    parser.add_argument(
        'X-Api-Token', location='headers', required=True,
        help='You must be authenticated to delete GWAS data. To authenticate we use Google OAuth2.0 access tokens. The easiest way to obtain an access token is through the [TwoSampleMR R](https://mrcieu.github.io/TwoSampleMR/#authentication) package using the `get_mrbase_access_token()` function.')
    parser.add_argument('id', type=str, required=True, help="Identifier to which the summary stats belong.")

    @api.expect(parser)
    def delete(self):
        logger_info()
        args = self.parser.parse_args()
        user_uid = get_user_email(request.headers.get('X-Api-Token'))
        delete_gwas(user_uid, args['id'])

        return {"message": "successfully deleted."}, 200


@api.route('/upload')
@api.doc(description="Upload GWAS summary stats file to MR Base")
class Upload(Resource):
    parser = api.parser()
    parser.add_argument(
        'X-Api-Token', location='headers', required=True,
        help='You must be authenticated to submit new GWAS data. To authenticate we use Google OAuth2.0 access tokens. The easiest way to obtain an access token is through the [TwoSampleMR R](https://mrcieu.github.io/TwoSampleMR/#authentication) package using the `get_mrbase_access_token()` function.')
    parser.add_argument('id', type=str, required=True,
                        help="Identifier to which the summary stats belong.")
    parser.add_argument('gwas_file', location='files', type=FileStorage, required=True,
                        help="Path to GWAS summary stats text file for upload.")
    parser.add_argument('chr_col', type=int, required=False, help="Column index for chromosome (0-indexed)")
    parser.add_argument('pos_col', type=int, required=False, help="Column index for base position (0-indexed)")
    parser.add_argument('snp_col', type=int, required=False, help="Column index for dbsnp rs-identifer (0-indexed)")
    parser.add_argument('ea_col', type=int, required=True, help="Column index for effect allele (0-indexed)")
    parser.add_argument('oa_col', type=int, required=True, help="Column index for non-effect allele (0-indexed)")
    parser.add_argument('eaf_col', type=int, required=False,
                        help="Column index for effect allele frequency (0-indexed)")
    parser.add_argument('beta_col', type=int, required=True, help="Column index for effect size (0-indexed)")
    parser.add_argument('se_col', type=int, required=True, help="Column index for standard error (0-indexed)")
    parser.add_argument('pval_col', type=int, required=True, help="Column index for P-value (0-indexed)")
    parser.add_argument('ncontrol_col', type=int, required=False,
                        help="Column index for control sample size; total sample size if continuous trait (0-indexed)")
    parser.add_argument('ncase_col', type=int, required=False, help="Column index for case sample size (0-indexed)")
    parser.add_argument('delimiter', type=str, required=True, choices=("comma", "tab"),
                        help="Column delimiter for file")
    parser.add_argument('header', type=str, required=True, help="Does the file have a header line?",
                        choices=('True', 'False'))
    parser.add_argument('gzipped', type=str, required=True, help="Is the file compressed with gzip?",
                        choices=('True', 'False'))

    @staticmethod
    def read_gzip(p, sep, args):
        with gzip.open(p, 'rt', encoding='utf-8') as f:
            if args['header'] == 'True':
                f.readline()

            for line in f:
                Upload.validate_row_with_schema(line.strip().split(sep), args)

    @staticmethod
    def read_plain_text(p, sep, args):
        with open(p, 'r') as f:
            if args['header'] == 'True':
                f.readline()

            for line in f:
                Upload.validate_row_with_schema(line.strip().split(sep), args)

    @staticmethod
    def md5(fname):
        hash_md5 = hashlib.md5()
        with open(fname, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    @staticmethod
    def validate_row_with_schema(line_split, args):
        row = dict()

        if 'chr_col' in args and args['chr_col'] is not None:
            row['chr'] = line_split[args['chr_col']]
        if 'pos_col' in args and args['pos_col'] is not None:
            row['pos'] = line_split[args['pos_col']]
        if 'ea_col' in args and args['ea_col'] is not None:
            row['ea'] = line_split[args['ea_col']]
        if 'oa_col' in args and args['oa_col'] is not None:
            row['oa'] = line_split[args['oa_col']]
        if 'eaf_col' in args and args['eaf_col'] is not None:
            row['eaf'] = line_split[args['eaf_col']]
        if 'beta_col' in args and args['beta_col'] is not None:
            row['beta'] = line_split[args['beta_col']]
        if 'se_col' in args and args['se_col'] is not None:
            row['se'] = line_split[args['se_col']]
        if 'pval_col' in args and args['pval_col'] is not None:
            row['pval'] = line_split[args['pval_col']]
        if 'ncontrol_col' in args and args['ncontrol_col'] is not None:
            row['ncontrol'] = line_split[args['ncontrol_col']]
        if 'ncase_col' in args and args['ncase_col'] is not None:
            row['ncase'] = line_split[args['ncase_col']]

        # check chrom pos or dbsnp is given
        if ('chr' not in row or 'pos' not in row) and 'snp' not in row:
            raise ValueError("Please provide chromosome and base-position (preferably) or dbsnp identifier.")

        # check row - raises validation exception if invalid
        schema = GwasRowSchema()
        schema.load(row)

    @api.expect(parser)
    def post(self):
        logger_info()
        args = self.parser.parse_args()
        study_folder = os.path.join(UPLOAD_FOLDER, args['id'])

        # make folder for new dataset
        if not os.path.exists(study_folder):
            os.makedirs(study_folder)

        output_path = os.path.join(study_folder, args['id'] + "_" + str(int(time.time())))
        args['gwas_file'].save(output_path)

        sep = None
        if args['delimiter'] == 'comma':
            sep = ","
        elif args['delimiter'] == 'tab':
            sep = "\t"

        try:
            if args['gzipped'] == 'True':
                Upload.read_gzip(output_path, sep, args)
            else:
                Upload.read_plain_text(output_path, sep, args)
        except OSError:
            return {'message': 'Could not read file. Check encoding'}, 400
        except marshmallow.exceptions.ValidationError as e:
            return {'message': 'The file format was invalid {}'.format(e)}, 400
        except IndexError as e:
            return {'message': 'Check column numbers and separator: {}'.format(e)}, 400

        # update the graph
        update_filename_and_path(str(args['id']), output_path, Upload.md5(output_path))

        return {'message': 'Upload successful'}, 201
