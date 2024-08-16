from flask import request, g
from flask_restx import Resource, Namespace, reqparse
import hashlib
import gzip
import json
import shutil
import requests
import logging
import os
import time
import re
import marshmallow.exceptions
from werkzeug.datastructures import FileStorage
from werkzeug.exceptions import BadRequest

from middleware.auth import jwt_required, check_role, key_required
from queries.cql_queries import *
from queries.gwas_info_node import GwasInfo
from resources.airflow import Airflow
from resources.globals import Globals
from resources.oci import OCI
from schemas.gwas_info_node_schema import GwasInfoNodeSchema, check_id_is_valid_filename
from schemas.gwas_row_schema import GwasRowSchema


logger = logging.getLogger('debug-log')

api = Namespace('edit', description="Upload and delete data")
gwas_info_model = api.model('GwasInfo', GwasInfoNodeSchema.get_flask_model())


def check_batch_exists(gwas_id, study_indexes):
    if gwas_id is None:
        return None
    try:
        reg = r'^([\w]+-[\w]+)-([\w]+)'
        study_prefix, study_id = re.match(reg, gwas_id).groups()
    except ValueError as e:
        raise BadRequest("ID is not in correct format <batch>-<section>-<id>: {}".format(gwas_id))
    if study_prefix not in study_indexes:
        raise BadRequest("Please use pre-existing batch or contact developers: {}".format(study_prefix))
    return study_prefix


def get_quota_by_roles(roles):
    if 'admin' in roles:
        return 10000
    if 'contributor' in roles:
        return 20
    return 0


@api.route('/list')
@api.doc(description="List metadata and DAG runs of all datasets that are added by the user")
class List(Resource):
    parser = api.parser()

    @api.expect(parser)
    @api.doc(id='edit_list_metadata')
    @jwt_required
    @check_role('contributor')
    def get(self):
        gwasinfo = get_gwas_added_by_user(g.user['uid'])

        dag_run = {
            'qc': {},
            'release': {}
        }
        airflow = Airflow()
        for id, gi_and_added_by in gwasinfo.items():
            if 'state' in gi_and_added_by['added_by']:
                if gi_and_added_by['added_by']['state'] >= 1:
                    dag_run['qc'][id] = airflow.get_dag_run('qc', id, True)
                    if gi_and_added_by['added_by']['state'] >= 3:
                        dag_run['release'][id] = airflow.get_dag_run('release', id, True)

        return {
            'definition': {
                'added_by_state': Globals.DATASET_ADDED_BY_STATE
            },
            'gwasinfo': gwasinfo,
            'dag_run': dag_run,
            'count': count_draft_gwas_of_user(g.user['uid']),
            'quota': get_quota_by_roles(g.user.get('role', []))
        }


@api.route('/add')
@api.doc(description="Add new gwas metadata")
class Add(Resource):
    parser = reqparse.RequestParser(bundle_errors=True)
    # Overwrite required=False for id
    parser.add_argument('id', type=str, required=False, help='Provide your own study identifier or leave blank for next continuous id.')
    GwasInfoNodeSchema.populate_parser(parser, ignore={GwasInfo.get_uid_key()})

    @api.expect(parser)
    @api.doc(id='edit_add_metadata')
    @jwt_required
    @check_role('contributor')
    def post(self):
        try:
            req = self.parser.parse_args()

            count = count_draft_gwas_of_user(g.user['uid'])
            quota = get_quota_by_roles(g.user.get('role', []))

            if count >= quota:
                return {"message": "You have reach your limit of adding metadata. You are allowed {} datasets but you already have {} that have not been released yet.".format(quota, count)}, 400

            if req['group_name'] is None:
                req['group_name'] = 'public'

            # use provided identifier if given
            check_id_is_valid_filename(req['id'])
            check_batch_exists(req['id'], Globals.all_batches)

            try:
                gwas_id = add_new_gwas(g.user['uid'], req, {req['group_name']}, gwas_id=req['id'])
            except Exception as e:
                return {"message": str(e)}, 400

            # write metadata to json
            # study_folder = os.path.join(Globals.UPLOAD_FOLDER, str(gwas_id))
            # try:
            #     os.makedirs(study_folder, exist_ok=True)
            # except FileExistsError as e:
            #     logger.error("Could not create study folder: {}".format(e))
            #     raise e
            #
            # gi = GwasInfo.get_node(gwas_id)
            # json_path = os.path.join(study_folder, str(gwas_id) + '.json')
            # with open(json_path, 'w') as f:
            #     json.dump(gi, f)
            # with open(json_path, 'rb') as f:
            #     oci_upload = OCI().object_storage_upload('upload', str(gwas_id) + '/' + str(gwas_id) + '.json', f)
            # shutil.rmtree(study_folder)
            #
            # return {"id": gwas_id, "oci_upload": {'status': oci_upload.status, 'headers': dict(oci_upload.headers)}}, 200

            return {'id': gwas_id}, 200

        except marshmallow.exceptions.ValidationError as e:
            raise BadRequest("Could not validate payload: {}".format(e))
        except ValueError as e:
            raise BadRequest("Could not add study: {}".format(e))


@api.route('/edit')
@api.doc(description="Edit existing GWAS metadata")
class Edit(Resource):
    parser = reqparse.RequestParser(bundle_errors=True)
    parser.add_argument('id', type=str, required=True, help='ID to be edited')
    GwasInfoNodeSchema.populate_parser(parser, ignore={GwasInfo.get_uid_key()})

    @api.expect(parser)
    @api.doc(id='edit_edit_metadata')
    @jwt_required
    @check_role('contributor')
    def post(self):
        try:
            req = self.parser.parse_args()

            try:
                state = check_gwasinfo_is_added_by_user(req['id'], g.user['uid'])
            except PermissionError as e:
                return {"message": str(e)}, 403

            if state is None or state != 0:
                return {"message": "Metadata cannot be modified once the QC pipeline has started"}, 400

            # use provided identifier if given
            check_id_is_valid_filename(req['id'])

            gwas_id = edit_existing_gwas(req['id'], req)

            # write metadata to json
            study_folder = os.path.join(Globals.UPLOAD_FOLDER, gwas_id)
            try:
                os.makedirs(study_folder, exist_ok=True)
            except FileExistsError as e:
                logger.error("Could not create study folder: {}".format(e))
                raise e

            oci = OCI()

            gi = GwasInfo.get_node(gwas_id)
            json_path = os.path.join(study_folder, str(gwas_id) + '.json')
            with open(json_path, 'w') as f:
                json.dump(gi, f)

            oci_response = {}
            with open(json_path, 'rb') as f:
                prefix = str(gwas_id) + '/' + str(gwas_id) + '.json'
                if len(oci.object_storage_list('upload', prefix)) > 0:
                    oci_upload_upload = oci.object_storage_upload('upload', prefix, f)
                    oci_response['upload'] = {'status': oci_upload_upload.status, 'headers': dict(oci_upload_upload.headers)}
                if len(oci.object_storage_list('data', prefix)) > 0:
                    oci_upload_data = oci.object_storage_upload('data', prefix, f)
                    oci_response['data'] = {'status': oci_upload_data.status, 'headers': dict(oci_upload_data.headers)}
            shutil.rmtree(study_folder)

            return {
                "gwas_info": gi,
                "oci": oci_response
            }, 200

        except marshmallow.exceptions.ValidationError as e:
            raise BadRequest("Could not validate payload: {}".format(e))
        except ValueError as e:
            raise BadRequest("Could not edit study: {}".format(e))


@api.route('/check/<gwas_id>')
@api.doc(description="Get metadata about specified GWAS summary datasets")
class GetId(Resource):
    parser = api.parser()

    @api.expect(parser)
    @api.doc(model=gwas_info_model, id='edit_get_metadata')
    @jwt_required
    @check_role('contributor')
    def get(self, gwas_id):
        try:
            recs = []
            for gwas_id in gwas_id.split(','):
                try:
                    recs.append(get_gwas_for_user(g.user['uid'], str(gwas_id), datapass=False))
                    # TODO: Optimise using single query
                    # TODO: WARNING - this is used by GwasDataImport to check whether a GWAS ID exists. It should not hide private datasets entirely.
                except LookupError:
                    continue
            return recs
        except LookupError:
            raise BadRequest("Gwas ID {} does not exist or you do not have permission to view.".format(gwas_id))


@api.route('/status/<gwas_id>')
@api.doc(description="Check the task instances of the DAG runs related to the dataset")
class TaskStatus(Resource):
    parser = api.parser()

    @api.expect(parser)
    @api.doc(id='edit_get_status')
    @jwt_required
    @check_role('contributor')
    def get(self, gwas_id):
        try:
            check_gwasinfo_is_added_by_user(gwas_id, g.user['uid'])
        except PermissionError as e:
            return {"message": str(e)}, 403

        airflow = Airflow()

        return {
            'definition': {
                'airflow_task_description': airflow.task_description
            },
            'dags': {
                'qc': {
                    'dag_run': airflow.get_dag_run('qc', gwas_id, True),
                    'task_instances': airflow.get_task_instances('qc', gwas_id)['tasks']
                },
                'release': {
                    'dag_run': airflow.get_dag_run('release', gwas_id, True),
                    'task_instances': airflow.get_task_instances('release', gwas_id)['tasks']
                }
            }
        }


@api.route('/delete/<gwas_id>')
@api.doc(description="For the given GWAS ID, delete metadata, uploaded files, QC proudct etc. BUT NOT `release` DAG and records in ES")
class Delete(Resource):
    parser = api.parser()
    parser.add_argument('fail_remaining_tasks', type=int, required=False, help='Whether to set the remaining tasks in DAG run as `failed` (which may take up to 90 secs) so that the instance can be terminated properly (1) or not (0)')
    parser.add_argument('delete_metadata', type=int, required=False, help='Whether to delete metadata (1) or only to delete files and pipeline products (0)')

    @api.doc(id='edit_delete_gwas')
    @jwt_required
    @check_role('contributor')
    def delete(self, gwas_id):
        args = self.parser.parse_args()

        try:
            state = check_gwasinfo_is_added_by_user(gwas_id, g.user['uid'])
        except PermissionError as e:
            return {"message": str(e)}, 403

        if args.get('fail_remaining_tasks', 0) == 0 and (state is None or state not in [0, 2]):
            return {"message": "Dataset cannot be deleted when the QC pipeline is still running or after it has been submitted for approval"}, 400

        study_folder = os.path.join(Globals.UPLOAD_FOLDER, gwas_id)
        if os.path.isdir(study_folder):
            shutil.rmtree(study_folder)

        oci = OCI()
        oci.object_storage_delete_by_prefix('upload', gwas_id + '/')

        airflow = Airflow()
        if args.get('fail_remaining_tasks', 0) == 1:
            airflow.fail_then_delete_dag_run('qc', gwas_id)
        else:
            airflow.delete_dag_run('qc', gwas_id)

        if args.get('delete_metadata', 0) == 1:
            delete_gwas(gwas_id)
            return {"message": "Deleted everything about " + gwas_id}, 200
        else:
            set_added_by_state_of_any_gwas(gwas_id, 0)
            return {"message": "Deleted uploaded file and QC products of " + gwas_id}, 200

        # TODO: Add workflow to delete from ieu-db-interface


@api.route('/upload')
@api.doc(description="Upload GWAS summary stats file to the IEU OpenGWAS database")
class Upload(Resource):
    parser = api.parser()
    parser.add_argument('chr_col', type=int, required=True, help="Column index for chromosome")
    parser.add_argument('pos_col', type=int, required=True, help="Column index for base position")
    parser.add_argument('ea_col', type=int, required=True, help="Column index for effect allele")
    parser.add_argument('oa_col', type=int, required=True, help="Column index for non-effect allele")
    parser.add_argument('beta_col', type=int, required=True, help="Column index for effect size")
    parser.add_argument('se_col', type=int, required=True, help="Column index for standard error")
    parser.add_argument('pval_col', type=int, required=True, help="Column index for P-value")
    parser.add_argument('delimiter', type=str, required=True, choices=("comma", "tab", "space"),
                        help="Column delimiter for file")
    parser.add_argument('header', type=str, required=True, help="Does the file have a header line?",
                        choices=('True', 'False'))
    parser.add_argument('ncase_col', type=int, required=False, help="Column index for case sample size")
    parser.add_argument('snp_col', type=int, required=False, help="Column index for dbsnp rs-identifer")
    parser.add_argument('eaf_col', type=int, required=False,
                        help="Column index for effect allele frequency")
    parser.add_argument('oaf_col', type=int, required=False,
                        help="Column index for other allele frequency")
    parser.add_argument('imp_z_col', type=int, required=False,
                        help="Column number for summary statistics imputation Z score")
    parser.add_argument('imp_info_col', type=int, required=False,
                        help="Column number for summary statistics imputation INFO score")
    parser.add_argument('ncontrol_col', type=int, required=False,
                        help="Column index for control sample size; total sample size if continuous trait")
    parser.add_argument('id', type=str, required=True,
                        help="Identifier to which the summary stats belong.")
    parser.add_argument('gwas_file', location='files', type=FileStorage, required=False,
                        help="Path to GWAS summary stats text file for upload. If you do not provide a file we assume the analysis is performed on HPC.")
    parser.add_argument('gzipped', type=str, required=True, help="Is the file compressed with gzip?",
                        choices=('True', 'False'))
    parser.add_argument('md5', type=str, required=False,
                        help="MD5 checksum of the uploaded file")
    parser.add_argument('nsnp', type=int, required=False, help="Number of snps in the uploaded file")

    @staticmethod
    def read_gzip(p, sep, args):
        conv = lambda i: i or None
        with gzip.open(p, 'rt', encoding='utf-8') as f:
            if args['header'] == 'True':
                f.readline()

            n = 0
            for line in f:
                n += 1
                if n > 1000:
                    break
                line_split = [conv(i) for i in line.strip().split(sep)]
                Upload.validate_row_with_schema(line_split, args)

            if n == 0:
                raise ValueError("File had 0 rows")

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

        # check row - raises validation exception if invalid
        schema = GwasRowSchema()
        schema.load(row)

    @staticmethod
    def __convert_index(val):
        try:
            return val - 1
        except TypeError:
            return val

    @api.expect(parser)
    @api.doc(id='edit_upload_gwas')
    @jwt_required
    @check_role('contributor')
    def post(self):
        args = self.parser.parse_args()

        try:
            state = check_gwasinfo_is_added_by_user(args['id'], g.user['uid'])
        except PermissionError as e:
            return {"message": str(e)}, 403

        if state is None or state != 0:
            return {"message": "Files cannot be re-uploaded once the QC pipeline has started"}, 400

        # convert to 0-based indexing
        args['chr_col'] = Upload.__convert_index(args['chr_col'])
        args['pos_col'] = Upload.__convert_index(args['pos_col'])
        args['ea_col'] = Upload.__convert_index(args['ea_col'])
        args['oa_col'] = Upload.__convert_index(args['oa_col'])
        args['beta_col'] = Upload.__convert_index(args['beta_col'])
        args['se_col'] = Upload.__convert_index(args['se_col'])
        args['pval_col'] = Upload.__convert_index(args['pval_col'])
        args['ncase_col'] = Upload.__convert_index(args['ncase_col'])
        args['snp_col'] = Upload.__convert_index(args['snp_col'])
        args['eaf_col'] = Upload.__convert_index(args['eaf_col'])
        args['imp_z_col'] = Upload.__convert_index(args['imp_z_col'])
        args['imp_info_col'] = Upload.__convert_index(args['imp_info_col'])
        args['ncontrol_col'] = Upload.__convert_index(args['ncontrol_col'])

        # fix delim
        if args['delimiter'] == "comma":
            args['delimiter'] = ","
        elif args['delimiter'] == "tab":
            args['delimiter'] = "\t"
        elif args['delimiter'] == "space":
            args['delimiter'] = " "

        study_prefix = check_batch_exists(args['id'], Globals.all_batches)
        study_folder = os.path.join(Globals.UPLOAD_FOLDER, args['id'])

        # create json payload
        data = dict()
        for k in args:
            if args[k] is not None and k not in ['id', 'gwas_file', 'gzipped', 'nsnp']:
                data[k] = args[k]

        # get build
        gwas_id = args['id']
        g_node = GwasInfo.get_node(gwas_id)
        data['build'] = g_node['build']

        # convert text to bool
        data['header'] = True if data['header'] == "True" else False

        if args['gwas_file'] is not None:

            if args['nsnp'] is not None:
                g_node['nsnp'] = args['nsnp']
                edit_existing_gwas(args['id'], g_node)
            elif g_node.get('nsnp', 0) == 0:
                return {"message": "The 'nsnp' (the number of SNPs in the uploaded file) field in metadata appears to be 0."}

            try:
                os.makedirs(study_folder, exist_ok=True)
            except FileExistsError as e:
                logger.error("Could not create study folder: {}".format(e))
                raise e

            input_data_filename = 'upload.txt.gz' if args['gzipped'] == 'True' else 'upload.txt'
            input_path = os.path.join(study_folder, input_data_filename)

            # save file to server
            args['gwas_file'].save(input_path)

            # check md5 sum
            if args['md5'] is not None:
                file_checksum = Upload.md5(input_path)
                try:
                    assert file_checksum == args['md5']
                except AssertionError as e:
                    logger.error("md5 doesn't match, upload: {}, stated: {}".format(file_checksum, args['md5']))
                    raise e

            # compress file
            if args['gzipped'] != 'True':
                with open(input_path, 'rb') as f_in:
                    with gzip.open(input_path + '.gz', 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                os.remove(input_path)
                input_data_filename += '.gz'
                input_path = os.path.join(study_folder, input_data_filename)

            try:
                Upload.read_gzip(input_path, args['delimiter'], args)
            except OSError:
                return {'message': 'Could not read file. Check encoding'}, 400
            except marshmallow.exceptions.ValidationError as e:
                return {'message': 'The file format was invalid {}'.format(e)}, 400
            except IndexError as e:
                return {'message': 'Check column numbers and separator: {}'.format(e)}, 400
            except ValueError as e:
                return {'message': 'Check file upload: {}'.format(e)}, 400

            oci = OCI()

            # write metadata to json
            gi = get_gwas_for_user(g.user['uid'], gwas_id, datapass=False)
            with open(os.path.join(study_folder, gwas_id + '.json'), 'w') as f:
                json.dump(gi, f)
            with open(os.path.join(study_folder, gwas_id + '.json'), 'rb') as f:
                oci_upload = oci.object_storage_upload('upload', gwas_id + '/' + gwas_id + '.json', f)

            # write analyst data to json
            # an = {"upload_uid": g.user['uid'], "upload_epoch": time.time()}
            # with open(os.path.join(study_folder, gwas_id + '_analyst.json'), 'w') as f:
            #     json.dump(an, f)
            # with open(os.path.join(study_folder, gwas_id + '_analyst.json'), 'rb') as f:
            #     oci_upload = oci.object_storage_upload('upload', gwas_id + '/' + gwas_id + '_analyst.json', f)

            # add cromwell label
            # with open(os.path.join(study_folder, gwas_id + '_labels.json'), 'w') as f:
            #     json.dump({"gwas_id": args['id']}, f)
            # with open(os.path.join(study_folder, gwas_id + '_labels.json'), 'rb') as f:
            #     oci_upload = oci.object_storage_upload('upload', gwas_id + '/' + gwas_id + '_labels.json', f)

            # write mappings, build, md5 etc. for pipeline
            with open(os.path.join(study_folder, gwas_id + '_data.json'), 'w') as f:
                json.dump(data, f)
            with open(os.path.join(study_folder, gwas_id + '_data.json'), 'rb') as f:
                oci_upload = oci.object_storage_upload('upload', gwas_id + '/' + gwas_id + '_data.json', f)

            # write params for workflow
            # wdl = {
            #     "qc.StudyId": str(args['id']),
            #     "qc.SumStatsFilename": str(input_data_filename),
            #     "elastic.StudyId": str(args['id']),
            #     "elastic.EsIndex": str(study_prefix),
            #     "elastic.Host": str(Globals.app_config['es']['host']),
            #     "elastic.Port": str(Globals.app_config['es']['port'])
            # }

            # conditionally add ncase & ncontrol
            # if g_node.get('ncase') is not None:
            #     wdl['qc.Cases'] = g_node['ncase']
            #
            # if g_node.get('ncontrol') is not None:
            #     wdl['qc.Controls'] = g_node['ncontrol']

            # with open(os.path.join(study_folder, gwas_id + '_wdl.json'), 'w') as f:
            #     json.dump(wdl, f)
            # with open(os.path.join(study_folder, gwas_id + '_wdl.json'), 'rb') as f:
            #     oci_upload = oci.object_storage_upload('upload', gwas_id + '/' + gwas_id + '_wdl.json', f)

            # upload to OCI Object Storage
            with open(input_path, 'rb') as f:
                oci_upload = oci.object_storage_upload('upload', gwas_id + '/' + input_data_filename, f)

            # add to workflow queue
            # r = requests.post(Globals.CROMWELL_URL + "/api/workflows/v1",
            #                   files={
            #                       'workflowSource': open(Globals.QC_WDL_PATH, 'rb'),
            #                       'labels': open(os.path.join(study_folder, str(args['id']) + '_labels.json'), 'rb'),
            #                       'workflowInputs': json.dumps(dict(filter(lambda item: item[0].startswith('qc.'), wdl.items())))
            #                   }, auth=Globals.CROMWELL_AUTH)
            # assert r.status_code == 201
            # assert r.json()['status'] == "Submitted"
            # logger.info("Submitted {} to workflow".format(r.json()['id']))

            airflow = Airflow().post_dag_run('qc', args['id'], {
                'url': oci.object_storage_par_create('upload', args['id'], 'AnyObjectReadWrite', 'Deny', 3600 * 36, args['id'] + '.qc'),
                'gwas_id': args['id'],
                'cohort_cases': g_node.get('ncase', None),
                'cohort_controls': g_node.get('ncontrol', None)
            })
            assert airflow['dag_run_id'] == args['id']
            logger.info("Submitted {} to qc workflow, nsnp = {}".format(airflow['dag_run_id'], g_node['nsnp']))

            shutil.rmtree(study_folder)

            set_added_by_state_of_any_gwas(args['id'], 1)

            return {'message': 'Dataset has been added to the pipeline', 'dag_id': 'qc', 'run_id': airflow['dag_run_id']}, 201
        else:
            return data, 200
