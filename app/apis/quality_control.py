from flask_restplus import Resource, Namespace
from queries.cql_queries import *
import marshmallow.exceptions
from werkzeug.exceptions import BadRequest
from resources.auth import get_user_email
from flask import request
import requests
import logging
import os
from resources.globals import Globals

logger = logging.getLogger('debug-log')

api = Namespace('quality_control', description="Quality control the GWAS data")
gwas_info_model = api.model('GwasInfo', GwasInfoNodeSchema.get_flask_model())


@api.route('/list')
@api.doc(description="Return all GWAS summary datasets requiring QC")
class List(Resource):
    parser = api.parser()
    parser.add_argument(
        'X-Api-Token', location='headers', required=False, default='null',
        help=Globals.AUTHTEXT)

    @api.expect(parser)
    @api.doc(model=gwas_info_model)
    def get(self):
        return get_todo_quality_control()


@api.route('/release')
@api.doc(description="Release data from quality control process")
class Release(Resource):
    parser = api.parser()
    parser.add_argument(
        'X-Api-Token', location='headers', required=True,
        help=Globals.AUTHTEXT)

    parser.add_argument('id', type=str, required=True, help='Identifier for the gwas info.')
    parser.add_argument('comments', type=str, required=False, help='Comments.')
    parser.add_argument('passed_qc', type=str, required=True, choices=("True", "False"), help='Did the data meet QC?')

    @api.expect(parser)
    def post(self):

        try:
            req = self.parser.parse_args()
            user_uid = get_user_email(request.headers.get('X-Api-Token'))

            try:
                check_user_is_admin(user_uid)
            except PermissionError as e:
                return {"message": str(e)}, 403

            # update graph
            gwas_info_id = req['id']
            add_quality_control(user_uid, gwas_info_id, req['passed_qc'] == "True", comment=req['comments'])

            # insert new data to elastic
            if req['passed_qc'] == "True":
                # find WDL params
                study_folder = os.path.join(Globals.UPLOAD_FOLDER, req['id'])

                # add to workflow queue
                r = requests.post(Globals.CROMWELL_URL + "/api/workflows/v1",
                                  files={'workflowSource': open(Globals.ELASTIC_WDL_PATH, 'rb'),
                                         'workflowInputs': open(os.path.join(study_folder, req['id'] + '_wdl.json'), 'rb')})
                assert r.status_code == 201
                assert r.json()['status'] == "Submitted"
                logger.info("Submitted {} to workflow".format(r.json()['id']))

                return {'message': 'Added to elastic import queue successful. Cromwell id :{}'.format(
                    r.json()['id'])}, 200

        except marshmallow.exceptions.ValidationError as e:
            raise BadRequest("Could not validate payload: {}".format(e))
        except requests.exceptions.HTTPError as e:
            raise BadRequest("Could not authenticate: {}".format(e))


@api.route('/delete')
@api.doc(description="Delete data from quality control process")
class Delete(Resource):
    parser = api.parser()
    parser.add_argument(
        'X-Api-Token', location='headers', required=True,
        help=Globals.AUTHTEXT)
    parser.add_argument('id', type=str, required=True, help='Identifier for the gwas info.')

    @api.expect(parser)
    def delete(self):

        try:
            req = self.parser.parse_args()
            user_uid = get_user_email(request.headers.get('X-Api-Token'))

            try:
                check_user_is_admin(user_uid)
            except PermissionError as e:
                return {"message": str(e)}, 403

            delete_quality_control(req['id'])

        except marshmallow.exceptions.ValidationError as e:
            raise BadRequest("Could not validate payload: {}".format(e))
        except requests.exceptions.HTTPError as e:
            raise BadRequest("Could not authenticate: {}".format(e))
