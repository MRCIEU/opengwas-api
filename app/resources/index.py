from flask_restful import Api, Resource, abort

class Index(Resource):
	def get(self):
		abort(503)

	def post(self):
		abort(503)

