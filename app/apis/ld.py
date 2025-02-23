from flask import g
from flask_restx import Resource, reqparse, abort, Namespace
import time

from resources.ld import *
from resources.globals import Globals
from middleware.auth import jwt_required
from middleware.limiter import limiter, get_allowance_by_user_tier, get_key_func_uid
from middleware.logger import logger as logger_middleware

api = Namespace('ld', description="LD operations e.g. clumping, tagging, LD matrices")


@api.route('/clump')
@api.doc(
    description="""
Perform clumping a specified set of rs IDs. 
Uses 1000 genomes reference data filtered to within-population MAF > 0.01 and only retaining SNPs.
""")
class Clump(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('rsid', type=str, required=False, action='append', default=[])
    parser.add_argument('pval', type=float, required=False, action='append', default=[])
    parser.add_argument('pthresh', type=float, required=False, default=5e-8)
    parser.add_argument('r2', type=float, required=False, default=0.001)
    parser.add_argument('kb', type=int, required=False, default=5000)
    parser.add_argument('pop', type=str, required=False, default="EUR", choices=Globals.LD_POPULATIONS)

    @api.expect(parser)
    @api.doc(id='ld_clump_post')
    @jwt_required
    def post(self):
        args = self.parser.parse_args()

        with limiter.shared_limit(limit_value=get_allowance_by_user_tier, scope='allowance_by_user_tier', key_func=get_key_func_uid, cost=12):
            pass

        if len(args['rsid']) == 0 or len(args['pval']) == 0 or len(args['rsid']) != len(args['pval']):
            abort(400)

        start_time = time.time()

        try:
            result = plink_clumping_rs(Globals.TMP_FOLDER, args['rsid'], args['pval'], args['pthresh'], args['pthresh'], args['r2'], args['kb'], args['pop'])
        except Exception as e:
            logger.error("Could not clump SNPs: {}".format(e))
            abort(503)

        logger_middleware.log(g.user['uuid'], 'ld_clump_post', start_time, {'rsid': len(args['rsid'])}, len(result))
        return result


@api.route('/matrix')
@api.doc(
    description="""
For a list of SNPs get the LD R values. These are presented relative to a specified reference allele.
Uses 1000 genomes reference data filtered to within-population MAF > 0.01 and only retaining SNPs.
""")
class LdMatrix(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('rsid', required=False, type=str, action='append', default=[])
    parser.add_argument('pop', type=str, required=False, default="EUR", choices=Globals.LD_POPULATIONS)
    
    @api.expect(parser)
    @api.doc(id='ld_matrix_post')
    @jwt_required
    @limiter.shared_limit(limit_value=get_allowance_by_user_tier, scope='allowance_by_user_tier', key_func=get_key_func_uid, cost=18)
    def post(self):
        args = self.parser.parse_args()

        start_time = time.time()

        try:
            result = plink_ldsquare_rs(Globals.TMP_FOLDER, args['rsid'], args['pop'])
        except Exception as e:
            logger.error("Could not clump SNPs: {}".format(e))
            abort(503)

        logger_middleware.log(g.user['uuid'], 'ld_matrix_post', start_time, {'rsid': len(args['rsid'])}, len(result['snplist']))
        return result


@api.route('/reflookup')
@api.doc(
    description="""
Lookup whether rsids are present in the LD reference panel
""")
class RefLookup(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('rsid', required=False, type=str, action='append', default=[])
    parser.add_argument('pop', type=str, required=False, default="EUR", choices=Globals.LD_POPULATIONS)

    @api.expect(parser)
    @api.doc(id='ld_reflookup_post')
    @jwt_required
    @limiter.shared_limit(limit_value=get_allowance_by_user_tier, scope='allowance_by_user_tier', key_func=get_key_func_uid, cost=2)
    def post(self):
        args = self.parser.parse_args()

        start_time = time.time()

        try:
            result = ld_ref_lookup(Globals.TMP_FOLDER, args['rsid'], args['pop'])
        except Exception as e:
            logger.error("Could not lookup SNPs: {}".format(e))
            abort(503)

        logger_middleware.log(g.user['uuid'], 'ld_reflookup_post', start_time, {'rsid': len(args['rsid'])}, len(result))
        return result
