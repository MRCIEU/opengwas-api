import base64
import json
import logging
import os
import requests
import shutil
import time

from flask import g, send_from_directory
from flask_restx import Resource, Namespace
import marshmallow.exceptions
from werkzeug.exceptions import BadRequest

from middleware.auth import jwt_required, check_role, check_role_is_sufficient
from queries.cql_queries import *
from resources.airflow import Airflow
from resources.globals import Globals
from resources._oci import OCIObjectStorage

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
            if not check_role_is_sufficient(g.user.get('roles', []), 'admin'):
                return {"message": str(e)}, 403

        try:
            report_str = OCIObjectStorage().object_storage_download('upload', '{}/{}_report.html'.format(gwas_id, gwas_id)).data.text
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
            return {"message": "The QC has failed so the dataset cannot be submitted for approval"}, 400

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

            airflow = Airflow().get_dag_run('qc', req['id'])
            if airflow.get('state', None) != 'success':
                raise ValueError("Dataset cannot be released - the QC workflow is in the state of: " + airflow['state'])

            # update graph
            gwas_id_n = add_quality_control(g.user['uid'], req['id'], req['passed_qc'] == "True", comment=req['comments'])['gwas_id_n']

            oci = OCIObjectStorage()

            if req['passed_qc'] == "True":
                airflow = Airflow().trigger_dag_run('release', req['id'], {
                    'url': oci.object_storage_par_create('upload', req['id'], 'AnyObjectReadWrite', 'Deny', 3600 * 4, req['id'] + '.es'),
                    'gwas_id': req['id'],
                    'gwas_id_n': gwas_id_n,
                })
                assert airflow['dag_run_id'] == req['id']
                logger.info("Submitted {} to es workflow".format(req['id']))

                set_added_by_state_of_any_gwas(req['id'], 4)

                for path in oci.object_storage_list('upload', req['id'] + '/'):
                    oci_copy = oci.object_storage_copy('upload', path, 'data', path)

                if os.environ.get('GROUP') in ['prod', 'test']:
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
