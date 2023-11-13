from flask import Flask, request
from flask_restx import Api, Namespace, Resource
from middleware.auth import validate_jwt, jwt_required
from middleware.limiter import limiter
from queries.cql_queries import *
from resources.globals import Globals
from resources.email import Email
from cryptography.fernet import Fernet
from werkzeug.exceptions import BadRequest
import logging
import jwt
import json
import time
import datetime

logger = logging.getLogger('debug-log')

api = Namespace('users', description='Users')


def generate_verification_link(email):
    fernet = Fernet(Globals.FERNET_KEY)
    expiry = int(time.time()) + Globals.EMAIL_VERIFICATION_LINK_VALIDITY
    message = fernet.encrypt(json.dumps({
        'email': email,
        'expiry': expiry
    }).encode())
    link = Api(Flask(__name__)).url_for(LoginViaLink, _external=True, message=message.decode())
    return link, expiry


@api.route('/send_verification_link')
@api.doc(description="Generate and send verification link to a given email address")
class SendVerificationLink(Resource):
    parser = api.parser()
    parser.add_argument('email', type=str, required=True, help='Provide your email address.')

    @api.expect(parser)
    @limiter.limit('20 per day')
    def get(self):
        # TODO: Validate email address by e.g. regex?
        req = self.parser.parse_args()

        link, expiry = generate_verification_link(req['email'])
        expiry_str = datetime.datetime.strftime(datetime.datetime.fromtimestamp(expiry).astimezone(), '%Y-%m-%d %H:%M:%S %Z')
        # result = {"link": link, "expiry": expiry_str}

        @limiter.limit('1 per day', key_func=lambda: req['email'])
        def __send():
            return Email().send_verification_email(link, req['email'], expiry_str)

        result = __send()
        return result


def validate_verification_link(message):
    fernet = Fernet(Globals.FERNET_KEY)
    try:
        message = json.loads(fernet.decrypt(message.encode()).decode())
        email = message['email']
    except Exception:
        raise BadRequest("Invalid verification link.")

    if int(time.time()) > message['expiry']:
        raise BadRequest("Verification link expired.")

    return email


def generate_jwt(uid, timestamp):
    result = jwt.encode({
        'uid': uid,
        'timestamp': timestamp
    }, Globals.JWT_KEY, algorithm='HS256')
    return result


def has_valid_names(user):
    return 'first_name' in user and user['first_name'] and 'last_name' in user and user['last_name']


@api.route('/login_via_link')
@api.doc(description="Validate the message from the email and generate JWT for the user")
class LoginViaLink(Resource):
    parser = api.parser()
    parser.add_argument('message', type=str, required=True,
                        help='Provide your verification message (link) from the email.')

    @api.expect(parser)
    def get(self):
        req = self.parser.parse_args()

        email = validate_verification_link(req['message'])

        user = get_user_by_email(email)
        if user is None:
            return {
                'message': "User does not exist.",
                'email': email
            }
        if not has_valid_names(user.data()['u']):
            return {
                'message': "User needs to use the registration link to provide their first and last name.",
                'email': email
            }

        jwt_timestamp = int(time.time())
        token = generate_jwt(email, jwt_timestamp)
        set_user_jwt_timestamp(email, jwt_timestamp)

        return {
            'uid': email,
            'token': token
        }


@api.route('/register')
@api.doc(description="Validate the message from the email and register the user")
class Register(Resource):
    parser = api.parser()
    parser.add_argument('message', type=str, required=True, help='Provide your verification message (link) from the email. ')
    parser.add_argument('first_name', type=str, required=True, help='Provide your first name.')
    parser.add_argument('last_name', type=str, required=True, help='Provide your last name.')

    @api.expect(parser)
    @limiter.limit('10 per day')
    def post(self):
        req = self.parser.parse_args()
        email = validate_verification_link(req['message'])

        # User will be created if the email address does not exist
        try:
            add_new_user(email, req['first_name'], req['last_name'])
            user = get_user_by_email(email)
        except Exception:
            raise BadRequest("Unable to create user.")

        # The user now exists but the names might be missing
        if has_valid_names(user.data()['u']):
            message = "Registered."
        else:
            try:
                set_user_names(email, req['first_name'], req['last_name'])
                message = "Names updated."
            except Exception:
                raise BadRequest("Unable to update user names.")

        return {
            'message': message + " Please use the link to generate a token.",
            'uid': email,
            'link': Api(Flask(__name__)).url_for(LoginViaLink, _external=True, message=req['message'])
        }


@api.route('/login_by_jwt')
@api.doc(description="Validate JWT and get user info")
class LoginByJWT(Resource):
    parser = api.parser()
    parser.add_argument('X-Api-JWT', location='headers', type=str, required=True, help='Provide your verification message (link) from the email')

    @api.expect(parser)
    def get(self):
        payload = validate_jwt(request.headers.get('X-Api-JWT'))
        return payload
