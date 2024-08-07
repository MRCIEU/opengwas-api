from flask import request, g
from flask_restx import Resource, Namespace
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

from middleware.auth import jwt_required
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


@api.route('/add')
@api.doc(description="Add new gwas metadata")
class Add(Resource):
    parser = api.parser()
    parser.add_argument('id', type=str, required=False,
                        help='Provide your own study identifier or leave blank for next continuous id.')
    GwasInfoNodeSchema.populate_parser(parser,
                                       ignore={GwasInfo.get_uid_key()})

    @api.expect(parser)
    @api.doc(id='edit_add_metadata')
    @jwt_required
    def post(self):
        try:
            req = self.parser.parse_args()

            try:
                check_user_is_developer(g.user['uid'])
            except PermissionError as e:
                return {"message": str(e)}, 403

            if req['group_name'] is None:
                req['group_name'] = 'public'

            # use provided identifier if given
            gwas_id_req = req['id']
            check_id_is_valid_filename(gwas_id_req)
            check_batch_exists(gwas_id_req, Globals.all_batches)

            req.pop('id')

            gwas_id = add_new_gwas(g.user['uid'], req, {req['group_name']}, gwas_id=gwas_id_req)

            # write metadata to json
            study_folder = os.path.join(Globals.UPLOAD_FOLDER, str(gwas_id))
            try:
                os.makedirs(study_folder, exist_ok=True)
            except FileExistsError as e:
                logger.error("Could not create study folder: {}".format(e))
                raise e

            gi = GwasInfo.get_node(gwas_id)
            json_path = os.path.join(study_folder, str(gwas_id) + '.json')
            with open(json_path, 'w') as f:
                json.dump(gi, f)
            with open(json_path, 'rb') as f:
                oci_upload = OCI().object_storage_upload('upload', str(gwas_id) + '/' + str(gwas_id) + '.json', f)
            shutil.rmtree(study_folder)

            return {"id": gwas_id, "oci_upload": {'status': oci_upload.status, 'headers': dict(oci_upload.headers)}}, 200

        except marshmallow.exceptions.ValidationError as e:
            raise BadRequest("Could not validate payload: {}".format(e))
        except ValueError as e:
            raise BadRequest("Could not add study: {}".format(e))


@api.route('/edit')
@api.doc(description="Edit existing GWAS metadata")
class Edit(Resource):
    parser = api.parser()
    parser.add_argument('id', type=str, required=True,
                        help='ID to be edited')
    GwasInfoNodeSchema.populate_parser(parser,
                                       ignore={GwasInfo.get_uid_key()})

    @api.expect(parser)
    @api.doc(id='edit_edit_metadata')
    @jwt_required
    def post(self):
        try:
            req = self.parser.parse_args()

            try:
                check_user_is_developer(g.user['uid'])
            except PermissionError as e:
                return {"message": str(e)}, 403

            # use provided identifier if given
            gwas_id = req['id']
            check_id_is_valid_filename(gwas_id)

            req.pop('id')

            gwas_uid = edit_existing_gwas(gwas_id, req)

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
            with open(json_path, 'rb') as f:
                prefix = str(gwas_id) + '/' + str(gwas_id) + '.json'
                if len(oci.object_storage_list('upload', prefix)) > 0:
                    oci_upload_upload = oci.object_storage_upload('upload', prefix, f)
                if len(oci.object_storage_list('data', prefix)) > 0:
                    oci_upload_data = oci.object_storage_upload('data', prefix, f)
            shutil.rmtree(study_folder)

            return {
                "gwas_info": gi,
                "oci": {
                    'upload': {'status': oci_upload_upload.status, 'headers': dict(oci_upload_upload.headers)},
                    'data': {'status': oci_upload_data.status, 'headers': dict(oci_upload_data.headers)}
                }
            }, 200

        except marshmallow.exceptions.ValidationError as e:
            raise BadRequest("Could not validate payload: {}".format(e))
        except ValueError as e:
            raise BadRequest("Could not add study: {}".format(e))


@api.route('/check/<gwas_info_id>')
@api.doc(description="Get metadata about specified GWAS summary datasets")
class GetId(Resource):
    parser = api.parser()

    @api.expect(parser)
    @api.doc(model=gwas_info_model, id='edit_get_metadata')
    @jwt_required
    def get(self, gwas_info_id):
        try:
            recs = []
            for gwas_id in gwas_info_id.split(','):
                try:
                    recs.append(get_gwas_for_user(g.user['uid'], str(gwas_id), datapass=False))
                    # TODO: Optimise using single query
                except LookupError:
                    continue
            return recs
        except LookupError:
            raise BadRequest("Gwas ID {} does not exist or you do not have permission to view.".format(gwas_info_id))


@api.route('/status/<gwas_id>')
@api.doc(description="Check on the progress of GWAS upload")
class JobStatus(Resource):
    parser = api.parser()

    @api.expect(parser)
    @api.doc(id='edit_get_status')
    @jwt_required
    def get(self, gwas_id):
        r = requests.get(Globals.CROMWELL_URL + "/api/workflows/v1/query", params=dict(label="gwas_id:" + gwas_id), auth=Globals.CROMWELL_AUTH)
        return r.json(), r.status_code


@api.route('/delete/<gwas_info_id>')
@api.doc(description="Delete gwas metadata")
class Delete(Resource):
    parser = api.parser()

    @api.expect(parser)
    @api.doc(id='edit_delete_gwas')
    @jwt_required
    def delete(self, gwas_info_id):
        args = self.parser.parse_args()

        try:
            check_user_is_developer(g.user['uid'])
        except PermissionError as e:
            return {"message": str(e)}, 403

        delete_gwas(gwas_info_id)
        study_folder = os.path.join(Globals.UPLOAD_FOLDER, gwas_info_id)
        if os.path.isdir(study_folder):
            shutil.rmtree(study_folder)

        oci = OCI()
        oci.object_storage_delete_by_prefix('upload', gwas_info_id + '/')
        oci.object_storage_delete_by_prefix('data', gwas_info_id + '/')

        airflow = Airflow()
        airflow.delete_dag_run('qc', gwas_info_id)
        airflow.delete_dag_run('es', gwas_info_id)

        # TODO: Add workflow to delete from ieu-db-interface

        return {"message": "Dataset deleted from object storage and pipeline."}, 200


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
                        help="MD5 checksum of upload file")

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
    def post(self):
        args = self.parser.parse_args()

        try:
            check_user_is_developer(g.user['uid'])
        except PermissionError as e:
            return {"message": str(e)}, 403

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
        j = dict()
        for k in args:
            if args[k] is not None and k != 'gwas_file' and k != 'gzipped':
                j[k] = args[k]

        # get build
        g_node = GwasInfo.get_node(j['id'])
        j['build'] = g_node['build']

        # convert text to bool
        j['header'] = True if j['header'] == "True" else False

        if args['gwas_file'] is not None:

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
            gwas_id = str(j['id'])
            del j['id']

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
                json.dump(j, f)
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
            logger.info("Submitted {} to qc workflow".format(airflow['dag_run_id']))

            shutil.rmtree(study_folder)

            return {'message': 'Dataset has been added to the pipeline', 'dag_id': 'qc', 'run_id': airflow['dag_run_id']}, 201
        else:
            return j, 200
