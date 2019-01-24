from flask_restplus import Resource, Namespace
from werkzeug.datastructures import FileStorage

api = Namespace('study', description="Add new study to database")

parser = api.parser()
parser.add_argument('X-Api-Token', location='headers', required=True,
                    help='You must be authenitcated to provide files. To authenticate we use Google OAuth2.0 access tokens. The easiest way to obtain an access token is through the [TwoSampleMR R](https://mrcieu.github.io/TwoSampleMR/#authentication) package using the `get_mrbase_access_token()` function.')
parser.add_argument('file', location='files', type=FileStorage, required=True, help="Path to GWAS summary stats.")


@api.route('/')
@api.doc(description="Upload GWAS summary stats")
class Upload(Resource):
    @api.expect(parser)
    def post(self):
        args = parser.parse_args()
        uploaded_file = args['file']
        with open(uploaded_file) as f:
            print(f.readline())
        return {'message': 'Upload successful'}, 201
