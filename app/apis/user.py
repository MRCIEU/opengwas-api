from flask import g, request
from flask_restx import Namespace, Resource
import datetime
from flask_limiter.util import get_remote_address

from middleware.auth import jwt_required
from middleware.limiter import limiter
from resources.globals import Globals


api = Namespace('user', description="User zone")


@api.route('')
@api.doc(description="Get information of the current user. This can be used to validate your token (status code will be 200 OK if successful). Read more at https://api.opengwas.io/api/#authentication")
class User(Resource):
    @api.doc(id='user_get', security=['token_jwt'])
    @limiter.limit('30 per hour')  # Max number of requests per IP
    @jwt_required
    def get(self):
        return {
            'user': {
                'account_id': g.user['uuid'],
                'uid': g.user['uid'],
                'first_name': g.user['first_name'],
                'last_name': g.user['last_name'],
                'most_recent_signin_method': Globals.USER_SOURCES[g.user['source']],
                'jwt_valid_until': datetime.datetime.strftime(datetime.datetime.fromtimestamp(g.user['jwt_timestamp'] + Globals.JWT_VALIDITY).astimezone(), '%Y-%m-%d %H:%M %Z'),
                'roles': g.user.get('role', [])
            },
            'request': {
                'client': request.headers.get('X-API-SOURCE', None),
                'ip': get_remote_address()
            }
        }
