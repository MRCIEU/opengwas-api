from flask import Blueprint, render_template, url_for, request, redirect, flash
from cryptography.fernet import Fernet
import time
import json
import datetime

from middleware import limiter, Validator
from queries.cql_queries import *
from resources import microsoft, GitHubUniversities
from resources.email import Email
from resources.globals import Globals
from .login_manager import *
from . import organisations


users_auth_bp = Blueprint('auth', __name__)


@users_auth_bp.route('/')
def show_signin_options():
    return render_template('users/signin.html', **microsoft.generate_signin_link(url_for('users.auth.signup_via_microsoft', _external=True)))


@users_auth_bp.route('/microsoft/redirect')
def signup_via_microsoft():
    try:
        microsoft.get_tokens(request.args)
    except Exception as e:
        flash(str(e), 'danger')
        return redirect(url_for('users.auth.show_signin_options'))

    user = _add_user_from_microsoft()
    signin_user(user)

    return redirect(url_for('users.index.index'))


def _add_user_from_microsoft():
    try:  # Parse Microsoft Graph API responses
        user_org_info = microsoft.get_user_and_org_info()
    except Exception as e:
        flash(str(e), 'danger')
        return redirect(url_for('users.auth.show_signin_options'))

    try:
        domain = user_org_info['user']['mail'].split("@")[1]
        if user_org_info['type'] == 'ORG':
            # Create/merge Org node
            org = organisations.get_or_add_org(provider='MS', domain=domain, new_org=user_org_info['organization'])
            # Create/merge User node as well as MEMBER_OF and MEMBER_OF_ORG relationships
            user = add_new_user(email=user_org_info['user']['mail'],
                         first_name=user_org_info['user']['givenName'], last_name=user_org_info['user']['surname'],
                         tier='ORG', org_uuid=org['uuid'], user_org_info=user_org_info['user_org'])

        else:
            # Just create/merge User node
            user = add_new_user(email=user_org_info['user']['mail'],
                         first_name=user_org_info['user']['givenName'], last_name=user_org_info['user']['surname'],
                         tier='PER')
    except Exception as e:
        flash(str(e), 'danger')
        return redirect(url_for('users.auth.show_signin_options'))

    return user.data()['u']


@users_auth_bp.route('/email/check')
@limiter.limit('30 per day')  # Max number of requests per IP
def check_email_and_names():
    req = request.args.to_dict()
    try:
        Validator('UserNodeSchema', partial=True).validate({'uid': req['email']})
    except Exception as e:
        return {'message': "Please provide a valid email address."}, 400

    user = get_user_by_email(req['email'])
    if user:
        return send_email(req['email'])

    try:
        Validator('UserNodeSchema', partial=True).validate({
            'uid': req["email"], 'first_name': req['first_name'], 'last_name': req['last_name']
        })
    except Exception as e:
        return {'message': "Please provide valid first name and last name."}, 400

    return send_email(req['email'], req['first_name'], req['last_name'])


@limiter.limit('15 per day')  # Max number of requests per IP
def send_email(email, first_name=None, last_name=None):
    link, expiry = _generate_email_signin_link(email, first_name, last_name)
    expiry_str = datetime.datetime.strftime(datetime.datetime.fromtimestamp(expiry).astimezone(), '%Y-%m-%d %H:%M:%S %Z')

    @limiter.limit('3 per day', key_func=lambda: email)  # Max number of requests per IP per recipient email address
    def __send():
        return Email().send_signin_email(link, email, expiry_str)

    try:
        result = __send()
    except Exception as e:
        return {
            'message': "Failed to send email. Please try again later or contact us. Details: " + str(e)
        }, 500
    return result


def _generate_email_signin_link(email, first_name=None, last_name=None):
    fernet = Fernet(Globals.app_config['fernet']['key'])
    expiry = int(time.time()) + Globals.EMAIL_VERIFICATION_LINK_VALIDITY
    message = fernet.encrypt(json.dumps({
        'email': email,
        'first_name': first_name,
        'last_name': last_name,
        'expiry': expiry
    }).encode())
    link = url_for('users.auth.signin_via_email', _external=True, message=message.decode())
    return link, expiry


@users_auth_bp.route('/email/signin')
def signin_via_email():
    req = request.args.to_dict()
    try:
        email, first_name, last_name = _decrypt_email_link(req["message"])
    except Exception as e:
        flash(str(e), 'danger')
        return redirect(url_for('users.auth.show_signin_options'))

    user = get_user_by_email(email)
    if user is None:
        return signup_via_email(email, first_name, last_name)

    signin_user(user.data()['u'])

    return redirect(url_for('users.index.index'))


def _decrypt_email_link(message):
    fernet = Fernet(Globals.app_config['fernet']['key'])
    try:
        message = json.loads(fernet.decrypt(message.encode()).decode())
        email = message['email']
        first_name = message['first_name']
        last_name = message['last_name']
        expiry = message['expiry']
    except Exception:
        raise Exception("Invalid sign in link. Please get a new one.")

    if int(time.time()) > expiry:
        raise Exception("Sign in link expired. Please get a new one.")

    return email, first_name, last_name


@users_auth_bp.route('/email/signup')
def signup_via_email(email, first_name, last_name):
    try:
        Validator('UserNodeSchema', partial=True).validate({
            'uid': email, 'first_name': first_name, 'last_name': last_name
        })
    except Exception:
        return {'message': "Please provide valid first name and last name."}, 400

    user = _add_user_from_email(email, first_name, last_name)
    signin_user(user)

    return redirect(url_for('users.index.index'))


def _add_user_from_email(email, first_name, last_name):
    try:
        domain = email.split("@")[1]
        org = organisations.get_or_add_org(provider='GH', domain=domain, new_org=GitHubUniversities().search_by_domain(domain))
        if org:
            user = add_new_user(email=email, first_name=first_name, last_name=last_name, tier='ORG', org_uuid=org['uuid'])
        else:
            user = add_new_user(email=email, first_name=first_name, last_name=last_name, tier='PER')
    except Exception as e:
        flash(str(e), 'danger')
        return redirect(url_for('users.auth.show_signin_options'))

    return user.data()['u']


@users_auth_bp.route('/signout')
def signout():
    sign_out_user()
    flash('You have successfully signed out. Please note your API tokens are still valid.')
    return redirect(url_for('users.auth.show_signin_options'))
