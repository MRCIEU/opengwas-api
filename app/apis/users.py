from flask import request
from flask_restx import Namespace, Resource
from middleware.auth import validate_jwt, jwt_required
from queries.cql_queries import *
from resources.globals import Globals
import logging
import jwt

logger = logging.getLogger('debug-log')

api = Namespace('users', description='Users')


def generate_jwt(uid, timestamp):
    result = jwt.encode({
        'uid': uid,
        'timestamp': timestamp
    }, Globals.app_config['jwt']['key'], algorithm='HS256')
    return result


@api.route('/signin_by_jwt')
@api.doc(description="Validate JWT and get user info")
class SignInByJWT(Resource):
    parser = api.parser()
    parser.add_argument('X-Api-JWT', location='headers', type=str, required=True, help='Provide your verification message (link) from the email')

    @api.expect(parser)
    def get(self):
        payload = validate_jwt(request.headers.get('X-Api-JWT'))
        return payload
