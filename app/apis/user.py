from flask import request
from flask_restx import Namespace, Resource
import datetime

from middleware.limiter import limiter
from resources.globals import Globals
from resources.jwt import validate_jwt


api = Namespace('user', description="User zone")


@api.route('')
@api.doc(description="Get information of the current user. This can be used to validate your token (status code will be 200 OK if successful). Read more at https://api.opengwas.io/api/#authentication")
class User(Resource):
    @api.doc(id='get_user', security=['token_jwt'])
    @limiter.limit('30 per hour')  # Max number of requests per IP
    def get(self):
        user = validate_jwt(request.headers.get('Authorization', '').replace("Bearer ", ""))
        return {
            'user': {
                'uid': user['uid'],
                'first_name': user['first_name'],
                'last_name': user['last_name'],
                'most_recent_signin_method': Globals.USER_SOURCES[user['source']],
                'jwt_valid_until': datetime.datetime.strftime(datetime.datetime.fromtimestamp(user['jwt_timestamp'] + Globals.JWT_VALIDITY).astimezone(), '%Y-%m-%d %H:%M %Z')
            }
        }
