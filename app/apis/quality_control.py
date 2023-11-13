from flask_restx import Resource, Namespace
from queries.cql_queries import *
import marshmallow.exceptions
from werkzeug.exceptions import BadRequest
from resources.auth import get_user_email
from flask import request, send_from_directory
import requests
import logging
import os
from resources.globals import Globals
import json
import time

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
    @api.doc(model=gwas_info_model, id='get_qc_todo')
    def get(self):
        return get_todo_quality_control()


@api.route('/report/<id>')
@api.doc(description="View html report on QC process for specified ID")
class GetId(Resource):
    parser = api.parser()
    parser.add_argument(
        'X-Api-Token', location='headers', required=False, default='null',
        help=Globals.AUTHTEXT)

    @api.expect(parser)
    @api.doc(id='get_report')
    def get(self, id):
        study_folder = os.path.join(Globals.UPLOAD_FOLDER, id)
        htmlfile = id + "_report.html"
        try:
            return send_from_directory(study_folder, htmlfile)
        except LookupError:
            raise BadRequest("GWAS ID {} does not have a html report file.".format(id))


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
    @api.doc(id='post_release')
    def post(self):
        try:
            req = self.parser.parse_args()
            user_uid = get_user_email(request.headers.get('X-Api-Token'))

            try:
                check_user_is_developer(user_uid)
            except PermissionError as e:
                return {"message": str(e)}, 403

            # check first stage workflow completed successfully
            payload = {'label': 'gwas_id:' + req['id']}
            r = requests.get(Globals.CROMWELL_URL + "/api/workflows/v1/query", params=payload)
            assert r.status_code == 200
            first_stage_passed = False
            for result in r.json()["results"]:
                if result["name"] == "qc":
                    if result["status"] == "Succeeded":
                        first_stage_passed = True
                        break
            if req['passed_qc'] == "True" and not first_stage_passed:
                raise ValueError("Cannot release data; the qc workflow failed!")

            # update graph
            add_quality_control(user_uid, req['id'], req['passed_qc'] == "True", comment=req['comments'])

            # update json
            study_folder = os.path.join(Globals.UPLOAD_FOLDER, req['id'])
            with open(os.path.join(study_folder, str(req['id']) + '_analyst.json'), 'r') as f:
                j = json.load(f)
            j['release_uid'] = user_uid
            j['release_epoch'] = time.time()
            j['release_comments'] = req['comments']
            j['passed_qc'] = req['passed_qc']
            with open(os.path.join(study_folder, str(req['id']) + '_analyst.json'), 'w') as f:
                json.dump(j, f)

            # insert new data to elastic
            if req['passed_qc'] == "True":
                # find WDL params
                # add to workflow queue
                r = requests.post(Globals.CROMWELL_URL + "/api/workflows/v1",
                                  files={'workflowSource': open(Globals.ELASTIC_WDL_PATH, 'rb'),
                                         'labels': open(os.path.join(study_folder, str(req['id']) + '_labels.json'),
                                                        'rb'),
                                         'workflowInputs': open(os.path.join(study_folder, req['id'] + '_wdl.json'),
                                                                'rb')})
                assert r.status_code == 201
                assert r.json()['status'] == "Submitted"
                logger.info("Submitted {} to workflow".format(r.json()['id']))

                # update GI cache
                requests.get(Globals.CROMWELL_URL + "/gicache")
                return {'message': 'Added to elastic import queue successful', 'job_id': r.json()['id']}, 200

        except marshmallow.exceptions.ValidationError as e:
            raise BadRequest("Could not validate payload: {}".format(e))
        except requests.exceptions.HTTPError as e:
            raise BadRequest("Could not authenticate: {}".format(e))
        except ValueError as e:
            raise BadRequest("Could not process request: {}".format(e))


@api.route('/check/<id>')
@api.doc(description="View files generated for a dataset")
class GetId(Resource):
    parser = api.parser()
    parser.add_argument(
        'X-Api-Token', location='headers', required=False, default='null',
        help=Globals.AUTHTEXT)

    @api.expect(parser)
    @api.doc(id='get_qc_files')
    def get(self, id):
        study_folder = os.path.join(Globals.UPLOAD_FOLDER, id)
        if os.path.isdir(study_folder):
            d = os.listdir(study_folder)
            return d
        else:
            return []


@api.route('/delete/<id>')
@api.doc(description="Delete data from quality control process")
class Delete(Resource):
    parser = api.parser()
    parser.add_argument(
        'X-Api-Token', location='headers', required=True,
        help=Globals.AUTHTEXT)
    parser.add_argument('id', type=str, required=True, help='Identifier for the gwas info.')

    @api.expect(parser)
    @api.doc(id='delete_qc')
    def delete(self, id):
        try:
            user_uid = get_user_email(request.headers.get('X-Api-Token'))

            try:
                check_user_is_developer(user_uid)
            except PermissionError as e:
                return {"message": str(e)}, 403

            delete_quality_control(id)

        except marshmallow.exceptions.ValidationError as e:
            raise BadRequest("Could not validate payload: {}".format(e))
        except requests.exceptions.HTTPError as e:
            raise BadRequest("Could not authenticate: {}".format(e))
