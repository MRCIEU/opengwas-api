from flask import g, send_file
from flask_restx import Resource, reqparse, abort, Namespace
import time

from queries.variants import *
from queries.vcf import *
from resources.globals import Globals
from middleware.auth import jwt_required
from middleware.limiter import limiter, get_allowance_by_user_source, get_key_func_uid
from middleware.logger import logger as logger_middleware

api = Namespace('variants', description="Retrieve variant information")


@api.route('/rsid/<rsid>')
@api.doc(
    description="Obtain information for a particular SNP or comma separated list of SNPs",
    params={
        'rsid': 'Comma-separated list of rs IDs to query from the GWAS IDs'
    }
)
class VariantGet(Resource):
    @api.doc(id='variants_get_rsid')
    @jwt_required
    def get(self, rsid=None):
        if rsid is None:
            abort(404)
        rsids = rsid.split(',')

        with limiter.shared_limit(limit_value=get_allowance_by_user_source, scope='allowance_by_user_source', key_func=get_key_func_uid, cost=1):
            pass

        start_time = time.time()

        try:
            total, hits = snps(rsids)
        except Exception as e:
            logger.error("Could not obtain variant information: {}".format(e))
            abort(503)

        logger_middleware.log(g.user['uuid'], 'variants_get_rsid', start_time, {'rsid': len(rsids)}, len(hits))
        return hits


@api.route('/rsid')
@api.doc(
    description="""
Obtain information for a particular SNP or comma separated list of SNPs. Note the payload can be passed to curl via json using e.g.:
```
-X POST -d '
{
    'rsid': ['rs234','rs333']
}
'
```
"""
)
class VariantPost(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('rsid', required=False, type=str, action='append', default=[], help="List of variant rs IDs")

    @api.expect(parser)
    @api.doc(id='variants_post_rsid')
    @jwt_required
    @limiter.shared_limit(limit_value=get_allowance_by_user_source, scope='allowance_by_user_source', key_func=get_key_func_uid, cost=1)
    def post(self):
        args = self.parser.parse_args()
        if len(args['rsid']) == 0:
            abort(400)

        start_time = time.time()

        try:
            total, hits = snps(args['rsid'])
        except Exception as e:
            logger.error("Could not obtain variant information: {}".format(e))
            abort(503)

        logger_middleware.log(g.user['uuid'], 'variants_post_rsid', start_time, {'rsid': len(args['rsid'])}, len(hits))
        return hits


@api.route('/chrpos/<chrpos>')
@api.doc(
    description="Obtain information for a particular variant or comma separated list of variants",
    params={
        'chrpos': 'Comma separated B37 coordinates or coordinate ranges e.g. 7:105561135-105563135,10:44865737'
    }
)
class ChrposGet(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('radius', type=int, required=False, default=0, help="Range to search either side of target locus")

    @api.expect(parser)
    @api.doc(id='variants_chrpos_get')
    @jwt_required
    @limiter.shared_limit(limit_value=get_allowance_by_user_source, scope='allowance_by_user_source', key_func=get_key_func_uid, cost=1)
    def get(self, chrpos):
        args = self.parser.parse_args()

        start_time = time.time()

        chrpos = [x for x in ''.join(chrpos.split()).split(',')]

        try:
            result = range_query(chrpos, args['radius'])
        except Exception as e:
            logger.error("Could not obtain variant information: {}".format(e))
            abort(503)

        logger_middleware.log(g.user['uuid'], 'variants_chrpos_get', start_time, {'chrpos': len(chrpos)}, len(result))
        return result


@api.route('/chrpos')
@api.doc(
    description="""
Obtain information for a particular variant or comma separated list of variants. Note the payload can be passed to curl via json using e.g.:

```
-X POST -d '
{
    'chrpos': ['7:105561135-105563135','10:44865737']
}
'
```

"""
)
class ChrposPost(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('chrpos', required=False, type=str, action='append', default=[],
                         help="List of variant chr:pos format on build 37 (e.g. 7:105561135)")
    parser.add_argument('radius', type=int, required=False, default=0,
                         help="Range to search either side of target locus")

    @api.expect(parser)
    @api.doc(id='variants_chrpos_post')
    @jwt_required
    @limiter.shared_limit(limit_value=get_allowance_by_user_source, scope='allowance_by_user_source', key_func=get_key_func_uid, cost=1)
    def post(self):
        args = self.parser.parse_args()
        if len(args['chrpos']) == 0:
            abort(400)

        start_time = time.time()

        try:
            result = range_query(args['chrpos'], args['radius'])
        except Exception as e:
            logger.error("Could not obtain variant information: {}".format(e))
            abort(503)

        logger_middleware.log(g.user['uuid'], 'variants_chrpos_post', start_time, {'chrpos': len(args['chrpos'])}, len(result))
        return result


@api.route('/gene/<gene>')
@api.doc(
    description="Obtain information for a particular SNP or comma separated list of SNPs",
    params={
        'gene': "A gene identifier, either Ensembl or Entrez, e.g. ENSG00000123374 or 1017"
    }
)
class GeneGet(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('radius', type=int, required=False, default=0, help="Range to search either side of target locus")

    @api.expect(parser)
    @api.doc(id='variants_gene_get')
    @jwt_required
    @limiter.shared_limit(limit_value=get_allowance_by_user_source, scope='allowance_by_user_source', key_func=get_key_func_uid, cost=1)
    def get(self, gene=None):
        args = self.parser.parse_args()

        start_time = time.time()

        try:
            total, hits = gene_query(gene, args['radius'])
        except Exception as e:
            logger.error("Could not obtain variant information: {}".format(e))
            abort(503)

        logger_middleware.log(g.user['uuid'], 'variants_gene_get', start_time, n_records=len(hits))
        return hits


@api.route('/afl2/rsid/<rsid>')
@api.doc(
    description="Obtain allele frequency and LD-scores for major populations based on 1000 genomes version 3 release",
    params={
        'rsid': 'Comma-separated list of rs IDs to query from the GWAS IDs'
    }
)
class VariantGet(Resource):
    @api.doc(id='variants_afl2_rsid_get')
    @jwt_required
    @limiter.shared_limit(limit_value=get_allowance_by_user_source, scope='allowance_by_user_source', key_func=get_key_func_uid, cost=1)
    def get(self, rsid=None):
        if rsid is None:
            abort(404)

        start_time = time.time()

        try:
            rsid = [x for x in ''.join(rsid.split()).split(',')]
        except Exception as e:
            logger.error("Could not parse rsid: {}".format(e))
            abort(503)

        try:
            result = vcf_rsid(rsid, Globals.AFL2['vcf'], Globals.AFL2['rsidx'])
        except Exception as e:
            logger.error("Could not obtain variant information: {}".format(e))
            abort(503)

        logger_middleware.log(g.user['uuid'], 'variants_afl2_rsid_get', start_time, {'rsid': len(rsid)}, n_records=len(result))
        return result


@api.route('/afl2/chrpos/<chrpos>')
@api.doc(
    description="Obtain allele frequency and LD-scores for major populations based on 1000 genomes version 3 release",
    params={
        'chrpos': 'Comma separated B37 coordinates or coordinate ranges e.g. 7:105561135-105563135,10:44865737'
    }
)
class ChrposGet(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('radius', type=int, required=False, default=0, help="Range to search either side of target locus")

    @api.expect(parser)
    @api.doc(id='variants_afl2_chrpos_get')
    @jwt_required
    @limiter.shared_limit(limit_value=get_allowance_by_user_source, scope='allowance_by_user_source', key_func=get_key_func_uid, cost=1)
    def get(self, chrpos=None):
        if chrpos is None:
            abort(404)
        args = self.parser.parse_args()

        start_time = time.time()

        try:
            chrpos = parse_chrpos([x for x in ''.join(chrpos.split()).split(',')], args['radius'])
        except Exception as e:
            logger.error("Could not parse chrpos: {}".format(e))
            abort(503)

        try:
            result = vcf_chrpos(chrpos, Globals.AFL2['vcf'])
        except Exception as e:
            logger.error("Could not obtain variant information: {}".format(e))
            abort(503)

        logger_middleware.log(g.user['uuid'], 'variants_afl2_chrpos_get', start_time, {'chrpos': len(chrpos)}, n_records=len(result))
        return result


@api.route('/afl2')
@api.doc(
    description="""
Obtain allele frequency and LD scores for a particular variant or comma separated list of variants.
```

"""
)
class Afl2Post(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('rsid', required=False, type=str, action='append', default=[], help="List of variant rs IDs")
    parser.add_argument('chrpos', required=False, type=str, action='append', default=[], help="List of variant chr:pos format on build 37 (e.g. 7:105561135)")
    parser.add_argument('radius', type=int, required=False, default=0, help="Range to search either side of target locus (for chrpos only)")

    @api.expect(parser)
    @api.doc(id='variants_afl2_post')
    @jwt_required
    @limiter.shared_limit(limit_value=get_allowance_by_user_source, scope='allowance_by_user_source', key_func=get_key_func_uid, cost=1)
    def post(self):
        args = self.parser.parse_args()
        if (len(args['chrpos']) == 0 and len(args['rsid']) == 0):
            abort(400)

        start_time = time.time()

        out1, out2 = [], []

        if len(args['chrpos']) != 0:
            try:
                chrpos = parse_chrpos(args['chrpos'], args['radius'])
            except Exception as e:
                logger.error("Could not parse chrpos: {}".format(e))
                abort(503)

            try:
                out1 = vcf_chrpos(chrpos, Globals.AFL2['vcf'])
            except Exception as e:
                logger.error("Could not obtain variant information: {}".format(e))
                abort(503)

        if len(args['rsid']) != 0:
            try:
                out2 = vcf_rsid(args['rsid'], Globals.AFL2['vcf'], Globals.AFL2['rsidx'])
            except Exception as e:
                logger.error("Could not obtain variant information: {}".format(e))
                abort(503)

        result = out1 + out2
        logger_middleware.log(g.user['uuid'], 'variants_afl2_post', start_time,
                              {'rsid': len(args['rsid']), 'chrpos': len(chrpos)}, n_records=len(result))
        return result


@api.route('/afl2/snplist')
@api.doc(description="Get list of rsids that are variable across populations for ancestry analyses")
class Afl2Snplist(Resource):
    @api.doc(id='variants_afl2_snplist_get')
    @jwt_required
    @limiter.shared_limit(limit_value=get_allowance_by_user_source, scope='allowance_by_user_source', key_func=get_key_func_uid, cost=10)
    def get(self):
        start_time = time.time()

        try:
            logger_middleware.log(g.user['uuid'], 'variants_afl2_snplist_get', start_time)
            return send_file(Globals.AFL2['snplist'])
        except Exception as e:
            logger.error("Could not obtain variant information: {}".format(e))
            abort(503)
