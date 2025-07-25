from flask import send_file, g
from flask_restx import Resource, Namespace
from werkzeug.exceptions import BadRequest
import logging
import os
import time

from middleware.auth import jwt_required
from middleware.limiter import limiter, get_allowance_by_user_tier, get_key_func_uid
from middleware.logger import logger as logger_middleware
from queries.cql_queries import *
from resources.globals import Globals
from resources._oci import OCIObjectStorage
from schemas.gwas_info_node_schema import GwasInfoNodeSchema

logger = logging.getLogger('debug-log')

api = Namespace('gwasinfo', description="Get information about available GWAS summary datasets")
gwas_info_model = api.model('GwasInfo', GwasInfoNodeSchema.get_flask_model())


def _get_cost(ids=None, files=0):
    if files == 0:
        if ids is None or len(ids) > 100:
            return 50
        return 1
    else:
        return len(ids) * 1000


@api.route('')
@api.doc(description="Get metadata about specified GWAS summary datasets (or all datasets if no id is specified)")
class Info(Resource):
    parser = api.parser()

    @api.expect(parser)
    @api.doc(model=gwas_info_model, id='gwasinfo_get_all')
    @jwt_required
    def get(self):
        with limiter.shared_limit(limit_value=get_allowance_by_user_tier, scope='allowance_by_user_tier', key_func=get_key_func_uid, cost=_get_cost()):
            pass
        # if g.user['uid'] is None and os.path.exists(Globals.STATIC_GWASINFO):
        #     return send_file(Globals.STATIC_GWASINFO)

        start_time = time.time()

        result = get_all_gwas_for_user(g.user['uid'])

        logger_middleware.log(g.user['uuid'], 'gwasinfo_get_all', start_time, {'id': 0}, len(result))
        return result

    parser.add_argument('id', required=False, type=str, action='append', default=[], help="List of GWAS IDs")

    @api.expect(parser)
    @api.doc(model=gwas_info_model, id='gwasinfo_post')
    @jwt_required
    def post(self):
        args = self.parser.parse_args()

        with limiter.shared_limit(limit_value=get_allowance_by_user_tier, scope='allowance_by_user_tier', key_func=get_key_func_uid, cost=_get_cost(args['id'])):
            pass

        start_time = time.time()

        if 'id' not in args or args['id'] is None or len(args['id']) == 0:
            result = get_all_gwas_for_user(g.user['uid'])
            logger_middleware.log(g.user['uuid'], 'gwasinfo_post', start_time, {'id': 0}, len(result))
            return result

        recs = []
        for gwas_info_id in args['id']:
            try:
                recs.append(get_gwas_for_user(g.user['uid'], str(gwas_info_id)))
            except LookupError as e:
                logger.warning("Could not locate study: {}".format(e))
                continue

        logger_middleware.log(g.user['uuid'], 'gwasinfo_post', start_time, {'id': len(args['id'])},
                              len(recs), [r['id'] for r in recs])
        return recs


@api.route('/<id>')
@api.doc(description="Get metadata about specified GWAS summary datasets")
class GetById(Resource):
    parser = api.parser()

    @api.expect(parser)
    @api.doc(model=gwas_info_model, id='gwasinfo_get')
    @jwt_required
    def get(self, id):
        ids = id.split(',')

        with limiter.shared_limit(limit_value=get_allowance_by_user_tier, scope='allowance_by_user_tier', key_func=get_key_func_uid, cost=_get_cost(ids)):
            pass

        start_time = time.time()

        try:
            recs = []
            for gwas_info_id in ids:
                try:
                    recs.append(get_gwas_for_user(g.user['uid'], str(gwas_info_id)))
                except LookupError:
                    continue
        except LookupError:
            raise BadRequest("Gwas ID {} does not exist or you do not have permission to view.".format(id))

        logger_middleware.log(g.user['uuid'], 'gwasinfo_get', start_time, {'id': len(ids)}, len(recs), [r['id'] for r in recs])
        return recs


@api.route('/files')
@api.doc(description="For each dataset specified, get the download URL for each file (.vcf.gz, .vcf.gz.tbi, _report.html) associated with the dataset. The URLs will expire in 2 hours. If a dataset is missing from the results, that means the dataset doesn't exist or you don't have access to it. If a dataset is in the result but some/all links are missing, that means the files are unavailable.")
class GetFilesByID(Resource):
    parser = api.parser()
    parser.add_argument('id', required=True, type=str, action='append', default=[], help="List of GWAS IDs")

    @api.expect(parser)
    @api.doc(id='gwasinfo_files_get')
    @jwt_required
    def post(self):
        args = self.parser.parse_args()

        with limiter.shared_limit(limit_value=get_allowance_by_user_tier, scope='allowance_by_user_tier', key_func=get_key_func_uid, cost=_get_cost(args['id'], 1)):
            pass

        start_time = time.time()

        try:
            recs = []
            for gwas_info_id in args['id']:
                try:
                    recs.append(get_gwas_for_user(g.user['uid'], str(gwas_info_id)))
                except LookupError:
                    continue
        except LookupError:
            raise BadRequest("Gwas ID does not exist or you do not have permission to view.")

        result = {}

        oci = OCIObjectStorage()
        for rec in recs:
            result[rec['id']] = [oci.object_storage_par_create('data', path, 'ObjectRead', 'Deny', 3600 * 2, g.user['uuid'] + '.' + rec['id'])
                                 for path in oci.object_storage_list('data', rec['id'] + '/')
                                 if path.endswith(('.vcf.gz', '.vcf.gz.tbi', '_report.html'))]


        logger_middleware.log(g.user['uuid'], 'gwasinfo_files_get', start_time, {'id': len(args['id'])}, len(recs), [r['id'] for r in recs])
        return result
