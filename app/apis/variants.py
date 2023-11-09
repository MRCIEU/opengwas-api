from flask_restplus import Resource, reqparse, abort, Namespace
from queries.variants import *
from resources.globals import Globals
from queries.vcf import *
from resources.auth import get_user_email
from flask import request, send_file

api = Namespace('variants', description="Retrieve variant information")


@api.route('/rsid/<rsid>')
@api.doc(
    description="Obtain information for a particular SNP or comma separated list of SNPs",
    params={
        'rsid': 'Comma-separated list of rs IDs to query from the GWAS IDs'
    }
)
class VariantGet(Resource):
    @api.doc(id='get_variant_rsid')
    def get(self, rsid=None):
        if rsid is None:
            abort(404)
        try:
            total, hits = snps(rsid.split(','))
        except Exception as e:
            logger.error("Could not obtain variant information: {}".format(e))
            abort(503)
        return hits


parser2 = reqparse.RequestParser()
parser2.add_argument('rsid', required=False, type=str, action='append', default=[], help="List of variant rs IDs")

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
    @api.expect(parser2)
    @api.doc(id='post_variant_rsid')
    def post(self):
        args = parser2.parse_args()

        if (len(args['rsid']) == 0):
            abort(405)
        try:
            total, hits = snps(args['rsid'])
        except Exception as e:
            logger.error("Could not obtain variant information: {}".format(e))
            abort(503)
        return hits



parser1 = reqparse.RequestParser()
parser1.add_argument('radius', type=int, required=False, default=0, help="Range to search either side of target locus")

@api.route('/chrpos/<chrpos>')
@api.expect(parser1)
@api.doc(
    description="Obtain information for a particular variant or comma separated list of variants",
    params={
        'chrpos': 'Comma separated B37 coordinates or coordinate ranges e.g. 7:105561135-105563135,10:44865737'
    }
)
class ChrposGet(Resource):
    @api.doc(id='get_chrpos')
    def get(self, chrpos, radius=0):
        args = parser1.parse_args()
        chrpos = [x for x in ''.join(chrpos.split()).split(',')]
        try:
            out = range_query(chrpos, args['radius'])
        except Exception as e:
            logger.error("Could not obtain variant information: {}".format(e))
            abort(503)
        return out


parser3 = reqparse.RequestParser()
parser3.add_argument('chrpos', required=False, type=str, action='append', default=[], help="List of variant chr:pos format on build 37 (e.g. 7:105561135)")
parser3.add_argument('radius', type=int, required=False, default=0, help="Range to search either side of target locus")

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
    @api.expect(parser3)
    @api.doc(id='post_chrpos')
    def post(self):
        args = parser3.parse_args()

        if (len(args['chrpos']) == 0):
            abort(405)
        try:
            out = range_query(args['chrpos'], args['radius'])
        except Exception as e:
            logger.error("Could not obtain variant information: {}".format(e))
            abort(503)
        return out



@api.route('/gene/<gene>')
@api.expect(parser1)
@api.doc(
    description="Obtain information for a particular SNP or comma separated list of SNPs",
    params={
        'gene': "A gene identifier, either Ensembl or Entrez, e.g. ENSG00000123374 or 1017"
    }
)
class GeneGet(Resource):
    @api.doc(id='get_gene')
    def get(self, gene=None):
        args = parser1.parse_args()
        try:
            total, hits = gene_query(gene, args['radius'])
        except Exception as e:
            logger.error("Could not obtain variant information: {}".format(e))
            abort(503)
        return hits


@api.route('/afl2/rsid/<rsid>')
@api.doc(
    description="Obtain allele frequency and LD-scores for major populations based on 1000 genomes version 3 release",
    params={
        'rsid': 'Comma-separated list of rs IDs to query from the GWAS IDs'
    }
)
class VariantGet(Resource):
    @api.doc(id='get_afl2_rsid')
    def get(self, rsid=None):
        if rsid is None:
            abort(404)

        try:
            rsid = [x for x in ''.join(rsid.split()).split(',')]
        except Exception as e:
            logger.error("Could not parse rsid: {}".format(e))
            abort(503)

        try:
            res = vcf_rsid(rsid, Globals.AFL2['vcf'], Globals.AFL2['rsidx'])
        except Exception as e:
            logger.error("Could not obtain variant information: {}".format(e))
            abort(503)
        return res


@api.route('/afl2/chrpos/<chrpos>')
@api.doc(
    description="Obtain allele frequency and LD-scores for major populations based on 1000 genomes version 3 release",
    params={
        'chrpos': 'Comma separated B37 coordinates or coordinate ranges e.g. 7:105561135-105563135,10:44865737'
    }
)
class ChrposGet(Resource):
    @api.doc(id='get_afl2_chrpos')
    def get(self, chrpos=None):
        if chrpos is None:
            abort(404)
        args = parser1.parse_args()
        try:
            chrpos = parse_chrpos([x for x in ''.join(chrpos.split()).split(',')], args['radius'])
        except Exception as e:
            logger.error("Could not parse chrpos: {}".format(e))
            abort(503)

        try:
            res = vcf_chrpos(chrpos, Globals.AFL2['vcf'])
        except Exception as e:
            logger.error("Could not obtain variant information: {}".format(e))
            abort(503)
        return res


parser4 = reqparse.RequestParser()
parser4.add_argument('rsid', required=False, type=str, action='append', default=[], help="List of variant rs IDs")
parser4.add_argument('chrpos', required=False, type=str, action='append', default=[], help="List of variant chr:pos format on build 37 (e.g. 7:105561135)")
parser4.add_argument('radius', type=int, required=False, default=0, help="Range to search either side of target locus (for chrpos only)")

@api.route('/afl2')
@api.doc(
    description="""
Obtain allele frequency and LD scores for a particular variant or comma separated list of variants.
```

"""
)
class Afl2Post(Resource):
    @api.expect(parser4)
    @api.doc(id='post_afl2')
    def post(self):
        args = parser4.parse_args()
        if (len(args['chrpos']) == 0 and len(args['rsid']) == 0):
            abort(405)

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
        else:
            out1 = []

        if len(args['rsid']) != 0:
            try:
                out2 = vcf_rsid(args['rsid'], Globals.AFL2['vcf'], Globals.AFL2['rsidx'])
            except Exception as e:
                logger.error("Could not obtain variant information: {}".format(e))
                abort(503)
        else:
            out2 = []

        return out1 + out2



@api.route('/afl2/snplist')
@api.doc(description="Get list of rsids that are variable across populations for ancestry analyses")
class Afl2Snplist(Resource):
    @api.doc(id='get_afl2_snplist')
    def get(self):
        try:
            return send_file(Globals.AFL2['snplist'])
        except Exception as e:
            logger.error("Could not obtain variant information: {}".format(e))
            abort(503)
