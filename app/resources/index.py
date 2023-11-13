from flask_restx import Resource
from flask import send_from_directory


class Index(Resource):
    def get(self):
        return send_from_directory(".", "index.html")
