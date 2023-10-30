from flask import Flask, request
from flask_restplus import Api, Namespace, Resource
from queries.cql_queries import *
from queries.user_node import User
from resources.globals import Globals
from resources.neo4j import Neo4j
from resources.cromwell import Cromwell
from cryptography.fernet import Fernet
from werkzeug.exceptions import BadRequest
import logging
import jwt
import json
import time
from schemas.user_node_schema import UserNodeSchema


logger = logging.getLogger('debug-log')

api = Namespace('users', description="Users")


@api.route('/send_verification_link')
@api.doc(description="Generate and send verification link to a given email address")
class SendVerificationLink(Resource):
    parser = api.parser()
    parser.add_argument('email', type=str, required=True, help='Provide your email address.')

    @api.expect(parser)
    def get(self):
        # TODO: Validate email address by e.g. regex?
        req = self.parser.parse_args()
        fernet = Fernet(Globals.FERNET_KEY)
        message = fernet.encrypt(json.dumps({
            "email": req['email'],
            "expiration": int(time.time()) + Globals.EMAIL_VERIFICATION_LINK_VALIDITY
        }).encode())
        print(message)
        return {"link": Api(Flask(__name__)).url_for(GenerateJWT, _external=True, message=message.decode())}


def generate_jwt(uid, timestamp):
    result = jwt.encode({
        "uid": uid,
        "timestamp": timestamp
    }, Globals.JWT_KEY, algorithm="HS256")
    return result


@api.route('/generate_jwt')
@api.doc(description="Validate the message in email and create the user (if necessary) and generate JWT")
class GenerateJWT(Resource):
    parser = api.parser()
    parser.add_argument('message', type=str, required=True,
                        help='Provide your verification message (link) from the email')

    @api.expect(parser)
    def get(self):
        req = self.parser.parse_args()
        fernet = Fernet(Globals.FERNET_KEY)
        try:
            message = json.loads(fernet.decrypt(req["message"].encode()).decode())
            email = message['email']
        except Exception:
            raise BadRequest("Invalid verification link.")

        if int(time.time()) > message['expiration']:
            raise BadRequest("Verification link expired.")

        user = get_user_by_email(email)
        if user is None:
            add_new_user(email)
            user = get_user_by_email(email)

        print(UserNodeSchema().load(user['u'])['uid'])

        jwt_timestamp = int(time.time())
        token = generate_jwt(email, jwt_timestamp)
        set_user_jwt_timestamp(email, jwt_timestamp)

        return {
            "uid": email,
            "token": token
        }


def validate_jwt(token):
    try:
        payload = jwt.decode(token, Globals.JWT_KEY, algorithms=['HS256'])
    except jwt.exceptions.InvalidSignatureError:
        raise BadRequest("Invalid JWT signature.")
    except jwt.exceptions.DecodeError:
        raise BadRequest("Invalid JWT header or payload.")

    user = get_user_by_email(payload['uid'])
    if user is None:
        raise BadRequest('User does not exist or has been deactivated.')
    user = UserNodeSchema().load(user['u'])
    if 'jwt_timestamp' not in user:
        raise BadRequest('Invalid JWT.')

    if payload['timestamp'] != user['jwt_timestamp']:
        raise BadRequest("Please generate a new token.")

    # TODO: add counter
    return user


@api.route('/login_by_jwt')
@api.doc(description="Validate JWT and get user info")
class LoginByJWT(Resource):
    def get(self):
        payload = validate_jwt(request.headers.get('X-Api-JWT'))
        return payload
