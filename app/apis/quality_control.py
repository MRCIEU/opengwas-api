import base64

from flask import g, send_from_directory
from flask_restx import Resource, Namespace
import marshmallow.exceptions
from werkzeug.exceptions import BadRequest

import json
import logging
import shutil
import os
import requests
import time

from .edit import check_batch_exists

from middleware.auth import jwt_required, check_role, check_role_is_sufficient
from queries.cql_queries import *
from resources.airflow import Airflow
from resources.globals import Globals
from resources.oci import OCI

logger = logging.getLogger('debug-log')

api = Namespace('quality_control', description="Quality control the GWAS data")
gwas_info_model = api.model('GwasInfo', GwasInfoNodeSchema.get_flask_model())


@api.route('/list')
@api.doc(description="Return all GWAS summary datasets requiring QC")
class List(Resource):
    parser = api.parser()

    @api.expect(parser)
    @api.doc(model=gwas_info_model, id='qc_get_todo')
    @jwt_required
    @check_role('admin')
    def get(self):
        return {
            'definition': {
                'added_by_state': Globals.DATASET_ADDED_BY_STATE
            },
            'gwasinfo': get_todo_quality_control()
        }


@api.route('/report/<gwas_id>')
@api.doc(description="View html report on QC process for specified ID")
class GetId(Resource):
    parser = api.parser()

    @api.expect(parser)
    @api.doc(id='qc_get_report')
    @jwt_required
    def get(self, gwas_id):
        try:
            gwasinfo = get_gwas_for_user(g.user['uid'], gwas_id, datapass=False)
        except Exception as e:
            if not check_role_is_sufficient(g.user.get('role', []), 'admin'):
                return {"message": str(e)}, 403

        try:
            report_str = OCI().object_storage_download('upload', '{}/{}_report.html'.format(gwas_id, gwas_id)).data.text
        except Exception as e:
            return {"message": "The report may not have been generated yet. Please check QC pipeline state."}, 404

        return {
            'filename': gwas_id + '_report.html',
            'content': str(base64.b64encode(report_str.encode('utf-8')), 'utf-8')
        }


@api.route('/submit/<gwas_id>')
@api.doc(description="Submit dataset for approval")
class TaskStatus(Resource):
    parser = api.parser()

    @api.expect(parser)
    @api.doc(id='qc_post_submit')
    @jwt_required
    @check_role('contributor')
    def get(self, gwas_id):
        try:
            status = check_gwasinfo_is_added_by_user(gwas_id, g.user['uid'])
        except PermissionError as e:
            return {"message": str(e)}, 403

        if status is None or status != 2:
            return {"message": "The QC pipeline must have been completed before the dataset can be submitted for approval"}, 400

        airflow = Airflow()
        dag_run = airflow.get_dag_run('qc', gwas_id)
        if dag_run['state'] != 'success':
            return {"message": "The QC has failed so the dataset cannot be submitted for approval"}

        set_added_by_state_of_any_gwas(gwas_id, 3)

        return {
            'message': 'Submitted for approval'
        }


@api.route('/release')
@api.doc(description="Release data from quality control process")
class Release(Resource):
    parser = api.parser()

    parser.add_argument('id', type=str, required=True, help='Identifier for the gwas info.')
    parser.add_argument('comments', type=str, required=False, help='Comments.')
    parser.add_argument('passed_qc', type=str, required=True, choices=("True", "False"), help='Did the data meet QC?')

    @api.expect(parser)
    @api.doc(id='qc_post_release')
    @jwt_required
    @check_role('admin')
    def post(self):
        try:
            req = self.parser.parse_args()

            # try:
            #     check_user_is_developer(g.user['uid'])
            # except PermissionError as e:
            #     return {"message": str(e)}, 403

            # check first stage workflow completed successfully
            # payload = {'label': 'gwas_id:' + req['id']}
            # r = requests.get(Globals.CROMWELL_URL + "/api/workflows/v1/query", params=payload, auth=Globals.CROMWELL_AUTH)
            # assert r.status_code == 200
            # first_stage_passed = False
            # for result in r.json()["results"]:
            #     if "name" in result and result["name"] == "qc" and result["status"] == "Succeeded":
            #         first_stage_passed = True
            #         break
            # if req['passed_qc'] == "True" and not first_stage_passed:
            #     raise ValueError("Cannot release data; the qc workflow failed!")

            airflow = Airflow().get_dag_run('qc', req['id'])
            if airflow['state'] != 'success':
                raise ValueError("Dataset cannot be released - the QC workflow is in the state of: " + airflow['state'])

            # Check submission status
            index = check_batch_exists(req['id'], Globals.all_batches)

            # update graph
            add_quality_control(g.user['uid'], req['id'], req['passed_qc'] == "True", comment=req['comments'])

            # update json
            # study_folder = os.path.join(Globals.UPLOAD_FOLDER, req['id'])
            # os.makedirs(study_folder, exist_ok=True)
            #
            oci = OCI()
            #
            # f = oci.object_storage_download('upload', str(req['id']) + '/' + str(req['id']) + '_analyst.json').data.text
            # analyst = json.loads(f)
            #
            # analyst['release_uid'] = g.user['uid']
            # analyst['release_epoch'] = time.time()
            # analyst['release_comments'] = req['comments']
            # analyst['passed_qc'] = req['passed_qc']
            #
            # with open(os.path.join(study_folder, str(req['id']) + '_analyst.json'), 'w') as f:
            #     json.dump(analyst, f)
            # with open(os.path.join(study_folder, str(req['id']) + '_analyst.json'), 'rb') as f:
            #     oci_upload = oci.object_storage_upload('upload', str(req['id']) + '/' + str(req['id']) + '_analyst.json', f)
            #
            # shutil.rmtree(study_folder)
            #
            # labels_str = oci.object_storage_download('upload', str(req['id']) + '/' + str(req['id']) + '_labels.json').data.text
            # wdl_str = oci.object_storage_download('upload', str(req['id']) + '/' + str(req['id']) + '_wdl.json').data.text

            # insert new data to elastic
            if req['passed_qc'] == "True":
                # find WDL params
                # add to workflow queue
                # r = requests.post(Globals.CROMWELL_URL + "/api/workflows/v1",
                #                   files={
                #                       'workflowSource': open(Globals.ELASTIC_WDL_PATH, 'rb'),
                #                       'labels': labels_str,
                #                       'workflowInputs': json.dumps(dict(filter(lambda item: item[0].startswith('elastic.'), json.loads(wdl_str).items())))
                #                   }, auth=Globals.CROMWELL_AUTH)
                # assert r.status_code == 201
                # assert r.json()['status'] == "Submitted"
                # logger.info("Submitted {} to workflow".format(r.json()['id']))

                airflow = Airflow().post_dag_run('release', req['id'], {
                    'url': oci.object_storage_par_create('upload', req['id'], 'AnyObjectReadWrite', 'Deny', 3600 * 4, req['id'] + '.es'),
                    'gwas_id': req['id'],
                    'index': index,
                    'es_host': Globals.ES_HOST,
                    'es_port': Globals.ES_PORT
                })
                assert airflow['dag_run_id'] == req['id']
                logger.info("Submitted {} to es workflow".format(req['id']))

                set_added_by_state_of_any_gwas(req['id'], 4)

                for file_name in [req['id'] + '.vcf.gz', req['id'] + '.vcf.gz.tbi', req['id'] + '_report.html']:
                    oci_copy = oci.object_storage_copy('upload', req['id'] + '/' + file_name, 'data', req['id'] + '/' + file_name)

                if Globals.app_config['env'] == 'production':
                    # update GI cache
                    requests.get(Globals.app_config['root_url'] + "/api/gicache")

                return {'message': 'Dataset has been added to the pipeline', 'dag_id': 'release', 'run_id': req['id']}, 200

        except marshmallow.exceptions.ValidationError as e:
            raise BadRequest("Could not validate payload: {}".format(e))
        except ValueError as e:
            raise BadRequest("Could not process request: {}".format(e))


@api.route('/check/<id>')
@api.doc(description="View files generated for a dataset")
class GetId(Resource):
    parser = api.parser()

    @api.expect(parser)
    @api.doc(id='qc_get_files')
    @jwt_required
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
    parser.add_argument('id', type=str, required=True, help='Identifier for the gwas info.')

    @api.expect(parser)
    @api.doc(id='qc_delete')
    @jwt_required
    def delete(self, id):
        try:
            try:
                check_user_is_developer(g.user['uid'])
            except PermissionError as e:
                return {"message": str(e)}, 403

            delete_quality_control(id)

        except marshmallow.exceptions.ValidationError as e:
            raise BadRequest("Could not validate payload: {}".format(e))
