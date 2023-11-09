from flask_restplus import Namespace, Resource
from resources.globals import Globals
from resources.neo4j import Neo4j
from resources.cromwell import Cromwell
import requests
import os

api = Namespace('batches', description="Data batches")


@api.route('')
@api.doc(description="List existing data batches")
class Status(Resource):
    @api.doc(id='get_batches')
    def get(self):
        return get_batches()

def get_batches():
    try:
        tx = Neo4j.get_db()
        res = []
        for r in tx.run("MATCH (n:Batches) return n"):
            d = r['n'].__dict__['_properties']
            res.append(d)
        return (res)
    except Exception as e:
        return None
