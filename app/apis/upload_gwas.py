from flask_restplus import Resource, Namespace
from werkzeug.datastructures import FileStorage
from resources._logger import *
from resources._globals import TMP_FOLDER
import os

api = Namespace('upload', description="Upload new GWAS summary stats")

parser = api.parser()
parser.add_argument('X-Api-Token', location='headers', required=True,
                    help='You must be authenitcated to provide files. To authenticate we use Google OAuth2.0 access tokens. The easiest way to obtain an access token is through the [TwoSampleMR R](https://mrcieu.github.io/TwoSampleMR/#authentication) package using the `get_mrbase_access_token()` function.')
parser.add_argument('file', location='files', type=FileStorage, required=True,
                    help="Path to GWAS summary stats text file for upload.")
parser.add_argument('sep', type=str, required=True, default='\t', help="Column separator for file")
parser.add_argument('skip_rows', type=int, required=True, help="Number of header lines to skip")

parser.add_argument('chr_idx', type=int, required=False, help="Column index for chromosome (0-indexed)")
parser.add_argument('pos_idx', type=int, required=False, help="Column index for base position (0-indexed)")
parser.add_argument('ea_idx', type=int, required=True, help="Column index for effect allele (0-indexed)")
parser.add_argument('nea_idx', type=int, required=True, help="Column index for non-effect allele (0-indexed)")
parser.add_argument('dbsnp_idx', type=int, required=False, help="Column index for rs identifer (0-indexed)")
parser.add_argument('ea_af_idx', type=int, required=False, help="Column index for effect allele frequency (0-indexed)")
parser.add_argument('effect_idx', type=int, required=True, help="Column index for effect size (0-indexed)")
parser.add_argument('se_idx', type=int, required=True, help="Column index for standard error (0-indexed)")
parser.add_argument('pval_idx', type=int, required=True, help="Column index for P-value (0-indexed)")
parser.add_argument('size_idx', type=int, required=False, help="Column index for study sample size (0-indexed)")
parser.add_argument('cases_idx', type=int, required=False,
                    help="Column index for number of cases (if case-control study); 0-indexed)")


@api.route('/', methods=["post"])
@api.doc(description="Upload GWAS summary stats")
class UploadGwas(Resource):

    @api.expect(parser)
    def post(self):
        args = parser.parse_args()
        uploaded_file = args['file']

        # read file
        contents = uploaded_file.read()

        # TODO validate file

        return {'message': 'Upload successful'}, 201
