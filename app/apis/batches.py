from flask_restx import Namespace, Resource

from middleware.limiter import limiter
from queries.cql_queries import *

api = Namespace('batches', description="Data batches")


@api.route('')
@api.doc(description="List existing data batches")
class Status(Resource):
    @api.doc(id='batches_get', security=[])
    @limiter.limit('30 per hour')  # Max number of requests per IP
    def get(self):
        try:
            return get_batches()
        except Exception as e:
            return None
