from flask_restx import Namespace, Resource, reqparse
import datetime
from flask_limiter.util import get_remote_address

from middleware import Validator
from middleware.auth import jwt_required, check_role
from profile.auth import _create_or_update_user_from_user_input
from queries.cql_queries import *
from resources.globals import Globals


api = Namespace('admin', description="Admin area")


@api.route('/users/list')
@api.hide
# List all users with sensitive info masked
class ListUsers(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('skip', type=int, required=False, default=0, help="Number of users to skip")
    parser.add_argument('limit', type=int, required=False, default=1000, help="Number of users to return")

    @api.doc(id='users_get', security=['token_jwt'])
    @jwt_required
    @check_role('admin')
    def get(self):
        args = self.parser.parse_args()

        users = []
        orgs = {}
        for uo in list_users_and_org(args['skip'], args['limit']):
            if uo['org'] is not None and uo['org']['uuid'] not in orgs:
                orgs[uo['org']['uuid']] = uo['org']
            users.append([
                uo['uid'],
                uo['uuid'],
                uo['org']['uuid'] if uo['org'] is not None else None,
                uo.get('last_name', None),
                uo['access_to'],
                uo.get('tags', None),
                uo.get('roles', None),
                uo.get('created', None),
                uo.get('last_signin', None)
            ])

        return {
            'users': users,
            'orgs': orgs
        }


@api.route('/users/add')
@api.hide
class AddUser(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('email', type=str, required=True, help="Email address (UID) of the user")
    parser.add_argument('first_name', type=str, required=True, help="First name of the user")
    parser.add_argument('last_name', type=str, required=True, help="Last name of the user")

    @api.doc(id='users_add_post', security=['token_jwt'])
    @jwt_required
    @check_role('admin')
    def post(self):
        args = self.parser.parse_args()

        try:
            Validator('UserNodeSchema', partial=True).validate({
                'uid': args['email'], 'first_name': args['first_name'], 'last_name': args['last_name']
            })
        except Exception as e:
            return {'message': "Please provide valid email address, first name and last name."}, 400

        if get_user_by_email(args['email']) is not None:
            return {'message': "User already exists"}, 400

        try:
            user = _create_or_update_user_from_user_input(args['email'], args['first_name'], args['last_name'], 'EM', return_redirect=False)
        except Exception as e:
            return {'message': str(e)}, 400

        return {
            'user': user
        }
