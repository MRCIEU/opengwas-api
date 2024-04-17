from flask import request, send_from_directory
from flask_restx import Resource, Namespace
import marshmallow.exceptions
from werkzeug.exceptions import BadRequest
import requests
import logging
import os
import json
import time

from queries.cql_queries import *
from resources.auth import get_user_email
from resources.globals import Globals
from resources.oci import OCI

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
            r = requests.get(Globals.CROMWELL_URL + "/api/workflows/v1/query", params=payload, auth=Globals.CROMWELL_AUTH)
            assert r.status_code == 200
            first_stage_passed = False
            for result in r.json()["results"]:
                if "name" in result and result["name"] == "qc" and result["status"] == "Succeeded":
                    first_stage_passed = True
                    break
            if req['passed_qc'] == "True" and not first_stage_passed:
                raise ValueError("Cannot release data; the qc workflow failed!")

            # update graph
            add_quality_control(user_uid, req['id'], req['passed_qc'] == "True", comment=req['comments'])

            # update json
            study_folder = os.path.join(Globals.UPLOAD_FOLDER, req['id'])
            os.makedirs(study_folder, exist_ok=True)

            oci = OCI()

            f = oci.object_storage_download('upload', str(req['id']) + '/' + str(req['id']) + '_analyst.json').data.text
            analyst = json.loads(f)

            analyst['release_uid'] = user_uid
            analyst['release_epoch'] = time.time()
            analyst['release_comments'] = req['comments']
            analyst['passed_qc'] = req['passed_qc']

            with open(os.path.join(study_folder, str(req['id']) + '_analyst.json'), 'w') as f:
                json.dump(analyst, f)
            with open(os.path.join(study_folder, str(req['id']) + '_analyst.json'), 'rb') as f:
                oci_upload = oci.object_storage_upload('upload', str(req['id']) + '/' + str(req['id']) + '_analyst.json', f)

            shutil.rmtree(study_folder)

            labels_str = oci.object_storage_download('upload', str(req['id']) + '/' + str(req['id']) + '_labels.json').data.text
            wdl_str = oci.object_storage_download('upload', str(req['id']) + '/' + str(req['id']) + '_wdl.json').data.text

            # insert new data to elastic
            if req['passed_qc'] == "True":
                # find WDL params
                # add to workflow queue
                r = requests.post(Globals.CROMWELL_URL + "/api/workflows/v1",
                                  files={
                                      'workflowSource': open(Globals.ELASTIC_WDL_PATH, 'rb'),
                                      'labels': labels_str,
                                      'workflowInputs': json.dumps(dict(filter(lambda item: item[0].startswith('elastic.'), json.loads(wdl_str).items())))
                                  }, auth=Globals.CROMWELL_AUTH)
                assert r.status_code == 201
                assert r.json()['status'] == "Submitted"
                logger.info("Submitted {} to workflow".format(r.json()['id']))

                if Globals.app_config['env'] == 'production':
                    # update GI cache
                    requests.get(Globals.app_config['root_url'] + "/api/gicache")

                # oci.object_storage_delete_by_prefix('upload', req['id'] + '/')

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
@api.doc(description="Delete quality control relationship (does not delete metadata or data files)")
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
