from flask_restplus import Resource, reqparse, abort, Namespace
from resources.ld import *
from resources.globals import Globals

api = Namespace('ld', description="LD operations e.g. clumping, tagging, LD matrices")
parser = reqparse.RequestParser()
parser.add_argument('rsid', type=str, required=False, action='append', default=[])
parser.add_argument('pval', type=float, required=False, action='append', default=[])
parser.add_argument('pthresh', type=float, required=False, default=5e-8)
parser.add_argument('r2', type=float, required=False, default=0.001)
parser.add_argument('kb', type=int, required=False, default=5000)
parser.add_argument('pop', type=str, required=False, default="EUR", choices=Globals.LD_POPULATIONS)


@api.route('/clump')
@api.doc(
    description="""
Perform clumping a specified set of rs IDs. 
Uses 1000 genomes reference data filtered to within-population MAF > 0.01 and only retaining SNPs.
""")
class Clump(Resource):

    @api.expect(parser)
    @api.doc(id='post_clump')
    def post(self):
        args = parser.parse_args()
        if (len(args['rsid']) == 0):
            abort(405)
        if (len(args['pval']) == 0):
            abort(405)
        if (len(args['rsid']) != len(args['pval'])):
            abort(405)

        try:
            out = plink_clumping_rs(Globals.TMP_FOLDER, args['rsid'], args['pval'], args['pthresh'], args['pthresh'],
                                    args['r2'], args['kb'], args['pop'])
        except Exception as e:
            logger.error("Could not clump SNPs: {}".format(e))
            abort(503)
        return out, 200


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
    def post(self):
        args = parser.parse_args()
        try:
            out = plink_ldsquare_rs(Globals.TMP_FOLDER, args['rsid'], args['pop'])
        except Exception as e:
            logger.error("Could not clump SNPs: {}".format(e))
            abort(503)
        return out, 200


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
    @api.doc(id='post_matrix')
    def post(self):
        args = parser.parse_args()
        try:
            out = ld_ref_lookup(Globals.TMP_FOLDER, args['rsid'], args['pop'])
        except Exception as e:
            logger.error("Could not lookup SNPs: {}".format(e))
            abort(503)
        return out, 200
