import json
import time

from flask import g
from flask_restx import Resource, reqparse, abort, Namespace
from opentelemetry.trace import SpanKind, Status, StatusCode

from resources.globals import Globals
from middleware.after_request import fix_legacy_value_errors
from middleware.auth import jwt_required
from middleware.limiter import limiter, get_allowance_by_user_tier, get_key_func_uid
from middleware.logger import logger as logger_middleware
from queries.assoc_queries_by_chunks import get_assoc_from_chunks
from queries.cql_queries import get_permitted_studies


api = Namespace('associations', description="Retrieve GWAS associations")


def _get_cost(ids=None, variants=None, proxies=0):  # Note: both inputs should be non-empty
    return max(len(ids), len(variants)) * (1 if proxies == 1 else 5)


@api.route('')
@api.doc(
    description="Get specific variant associations from specific GWAS datasets"
)
class AssocPost(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('variant', type=str, required=True, action='append',
                         help="List of variants as rsid or chr:pos or chr:pos1-pos2 where positions are in hg19/b37 e.g. ['rs1205', '7:105561135', '7:105561135-105563135']")
    parser.add_argument('id', type=str, required=True, action='append',
                        help="List of GWAS study IDs e.g. ['ieu-a-2', 'ieu-a-7']")
    parser.add_argument('proxies', type=int, required=False, default=0,
                         help="Whether to look for proxies (1) or not (0). Note that proxies won't be looked for range queries")
    parser.add_argument('r2', type=float, required=False, default=0.8,
                        help="Minimum LD r2 for a proxy")
    parser.add_argument('align_alleles', type=int, required=False, default=1,
                        help="Whether to align alleles")
    parser.add_argument('palindromes', type=int, required=False, default=1,
                         help="Whether to allow palindromic proxies")
    parser.add_argument('maf_threshold', type=float, required=False, default=0.3,
                         help="Maximum MAF allowed for a palindromic variant")

    @api.expect(parser)
    @api.doc(id='assoc_post')
    @jwt_required
    def post(self):
        args = self.parser.parse_args()

        with limiter.shared_limit(limit_value=get_allowance_by_user_tier, scope='allowance_by_user_tier',
                                  key_func=get_key_func_uid,
                                  cost=_get_cost(args['id'], args['variant'], args['proxies'])):
            pass

        time_start = time.time()

        with Globals.tracer.start_as_current_span("assoc", kind=SpanKind.SERVER) as span:
            span.set_attribute('uuid', g.user['uuid'])

            # Check arguments
            with Globals.tracer.start_as_current_span("assoc.check_args", kind=SpanKind.SERVER) as span:
                if len(args['id']) == 0 or len(args['variant']) == 0:
                    span.set_status(Status(StatusCode.ERROR, "EMPTY_ID_OR_VARIANT_LIST"))
                    return {
                        "message": "Please provide at least one id and one variant.",
                    }, 400

                if len(args['id']) * len(args['variant']) > 64:
                    span.set_status(Status(StatusCode.ERROR, "TOO_MANY_ID_VARIANT_COMBINATIONS"))
                    return {
                        "message": "Please make sure N(id) * N(variant) <= 64.",
                    }, 400

                span.set_attribute('n_id_variant_combs', len(args['id']) * len(args['variant']))

            # Check access
            with Globals.tracer.start_as_current_span("assoc.check_access", kind=SpanKind.SERVER) as span:
                gwasinfo_permitted = get_permitted_studies(g.user['uid'], args['id'])
                gwas_ids_permitted = list(gwasinfo_permitted.keys())
                if len(gwas_ids_permitted) == 0:
                    return []

            # Query assoc
            with Globals.tracer.start_as_current_span("assoc.query", kind=SpanKind.SERVER) as span:
                try:
                    result, n_chunks_accessed, time_ms = get_assoc_from_chunks(gwasinfo_permitted, args['variant'], gwas_ids_permitted, args['proxies'], args['r2'], args['align_alleles'], args['palindromes'], args['maf_threshold'])
                except Exception as e:
                    span.set_attributes({
                        'args': json.dumps(args),
                    })
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, "UNABLE_TO_RETRIEVE_ASSOCIATIONS"))
                    return {
                        "message": "Unable to retrieve associations.",
                        "trace_id": format(span.get_span_context().trace_id, '016x'),
                    }, 503

                span.set_attributes({
                    'n_chunks': n_chunks_accessed,
                    'n_results': len(result),
                })
                if n_chunks_accessed > 0:
                    Globals.meters['histogram_time_per_chunk'].record(round(time_ms / n_chunks_accessed))

            span.set_status(Status(StatusCode.OK))

        logger_middleware.log(g.user['uuid'], 'assoc_chunked_post', time_start,
                              {'id': len(args['id']), 'variant': len(args['variant']), 'proxies': args['proxies'],
                               'chunks': n_chunks_accessed},
                              len(result), list(set([r['id'] for r in result])),
                              len(set([r['rsid'] for r in result])))

        return fix_legacy_value_errors(result)
