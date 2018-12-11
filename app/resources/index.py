from flask_restful import Api, Resource, abort
from flask import send_from_directory
from _logger import *

class Index(Resource):
    def get(self):
		logger_info()
        return send_from_directory(".", "index.html")


