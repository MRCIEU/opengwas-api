from flask_restplus import Resource, reqparse, abort, Namespace, fields
from resources._globals import *
from resources._logger import *
from resources._ld import *

api = Namespace('ld', description="LD operations e.g. clumping, tagging, LD matrices")
parser = reqparse.RequestParser()
parser.add_argument('rsid', type=str, required=False, action='append', default=[])
parser.add_argument('pval', type=float, required=False, action='append', default=[])
parser.add_argument('pthresh', type=float, required=False, default=5e-8)
parser.add_argument('r2', type=float, required=False, default=0.001)
parser.add_argument('kb', type=int, required=False, default=5000)


@api.route('/clump')
@api.doc(
    description="""
Perform clumping a specified set of rs IDs. Note the payload can be passed to curl via json using:

```
-X POST -d '
{
    'parameters': 'etc'
}
'
```
""")
class Clump(Resource):

    @api.expect(parser)
    def post(self):
        logger_info()
        args = parser.parse_args()
        if (len(args['rsid']) == 0):
            abort(405)
        if (len(args['pval']) == 0):
            abort(405)
        if (len(args['rsid']) != len(args['pval'])):
            abort(405)

        try:
            out = plink_clumping_rs(TMP_FOLDER, args['rsid'], args['pval'], args['pthresh'], args['pthresh'],
                                    args['r2'], args['kb'])
        except:
            abort(503)
        return out, 200


@api.route('/matrix')
@api.doc(
    description="""
For a list of SNPs get the LD R values. These are presented relative to a specified reference allele. Note the payload can be passed to curl via json using:

```
-X POST -d '
{
    'parameters': 'etc'
}
'
```
""")
class LdMatrix(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('rsid', required=False, type=str, action='append', default=[])

    @api.expect(parser)
    def post(self):
        logger_info()
        args = parser.parse_args()
        try:
            out = plink_ldsquare_rs(TMP_FOLDER, args['rsid'])
        except:
            abort(503)
        return out, 200
