from flask_restx import Namespace, Resource

from resources.neo4j import Neo4j
from middleware.limiter import limiter

api = Namespace('batches', description="Data batches")


@api.route('')
@api.doc(description="List existing data batches")
class Status(Resource):
    @api.doc(id='batches_get', security=[])
    @limiter.limit('30 per hour')  # Max number of requests per IP
    def get(self):
        try:
            res = []
            for r in Neo4j.get_db().run("MATCH (n:Batches) return n"):
                res.append(r['n'].__dict__['_properties'])
            return res
        except Exception as e:
            return None
