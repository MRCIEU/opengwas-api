from flask_restplus import Resource, reqparse, Namespace, fields
from resources._logger import *
from queries.cql_queries import *
import marshmallow.exceptions
from werkzeug.exceptions import BadRequest

api = Namespace('quality_control', description="Quality control the GWAS data")


@api.route('/release')
@api.doc(description="Release data from quality control process")
class Release(Resource):
    parser = api.parser()
    parser.add_argument(
        'X-Api-Token', location='headers', required=True,
        help='You must be authenticated to submit new GWAS data. To authenticate we use Google OAuth2.0 access tokens. The easiest way to obtain an access token is through the [TwoSampleMR R](https://mrcieu.github.io/TwoSampleMR/#authentication) package using the `get_mrbase_access_token()` function.')
    parser.add_argument('id', type=str, required=True, help='Identifier for the gwas info.')
    parser.add_argument('comments', type=str, required=False, help='Comments.')
    parser.add_argument('passed_qc', type=str, required=True, choices=("True", "False"), help='Did the data meet QC?')

    @api.expect(parser)
    def post(self):
        logger_info()

        try:
            req = self.parser.parse_args()
            user_uid = get_user_email(request.headers.get('X-Api-Token'))
            gwas_info_id = req['id']

            add_quality_control(user_uid, gwas_info_id, data_passed=req['passed_qc'] == "True", comment=req['comments'])

        except marshmallow.exceptions.ValidationError as e:
            raise BadRequest("Could not validate payload: {}".format(e))


@api.route('/delete')
@api.doc(description="Release data from quality control process")
class Delete(Resource):
    parser = api.parser()
    parser.add_argument(
        'X-Api-Token', location='headers', required=True,
        help='You must be authenticated to submit new GWAS data. To authenticate we use Google OAuth2.0 access tokens. The easiest way to obtain an access token is through the [TwoSampleMR R](https://mrcieu.github.io/TwoSampleMR/#authentication) package using the `get_mrbase_access_token()` function.')
    parser.add_argument('id', type=str, required=True, help='Identifier for the gwas info.')

    @api.expect(parser)
    def delete(self):
        logger_info()

        try:
            req = self.parser.parse_args()
            delete_quality_control(req['id'])

        except marshmallow.exceptions.ValidationError as e:
            raise BadRequest("Could not validate payload: {}".format(e))
