import json
import re

from flask import Blueprint, render_template, g, request
from flask_login import login_required, current_user

from queries.cql_queries import *
from queries.es_user import *
from queries.redis_queries import RedisQueries
from resources import CryptographyTool
from resources.globals import Globals
from middleware.auth import get_user_tier
from middleware.limiter import limiter, get_allowance_by_user_tier, get_key_func_uid


profile_index_bp = Blueprint('index', __name__)


@profile_index_bp.route('')
@login_required
def index():
    g.user = current_user
    return render_template('profile/index.html', user=current_user, globals_sources=Globals.USER_SOURCES,
                           globals_tiers=Globals.USER_TIERS, user_tier=get_user_tier(),
                           allowance_by_user_tier=get_allowance_by_user_tier(), root_url=Globals.app_config['root_url'])


@profile_index_bp.route('/data')
@login_required
def gdpr():
    g.user = current_user
    computed_org, computed_membership = get_org_and_membership_from_user(current_user['uid']) if current_user['group'] == 'ORG' else (None, None)
    return render_template('profile/data.html', user=current_user, globals_sources=Globals.USER_SOURCES, computed_org=computed_org, computed_membership=computed_membership)


@profile_index_bp.route('/test_allowance')
@login_required
def get_allowance():
    g.user = current_user
    with limiter.shared_limit(limit_value=get_allowance_by_user_tier, scope='allowance_by_user_tier', key_func=get_key_func_uid, deduct_when=lambda flask_response: False):
        pass
    return {}


@profile_index_bp.route('/surveys/finalise/<form_id>')
@login_required
def finalise_survey(form_id):
    return render_template('profile/surveys/finalise.html', form_id=form_id)


@profile_index_bp.route('/surveys/list')
@login_required
def list_surveys():
    g.user = current_user

    return {
        'uid': g.user['uid'],
        'uuid_encrypted': CryptographyTool().encrypt(g.user['uuid']).decode(),
        'surveys': Globals.SURVEY_FORMS
    }


@profile_index_bp.route('/surveys/parse')
@login_required
def parse_survey():
    g.user = current_user
    survey_form_key = request.args.get('form', None)
    message = ''

    if survey_form_key is not None:
        message = parse_survey_response(survey_form_key, g.user['uuid'])

    return {
        'uuid': g.user['uuid'],
        'form': survey_form_key,
        'message': message
    }


def parse_survey_response(survey_form_key, uuid):
    def escape_and_strip(input):
        return re.sub(r'[^a-zA-Z0-9_()\s-]', '', input).strip()

    try:
        raw_response = RedisQueries('cache').get_cache('tally' + '_' + Globals.SURVEY_FORMS[survey_form_key], uuid)
    except KeyError:  # key not found in Redis
        return "Unable to find the survey."

    if raw_response is None:
        return "Unable to find your response to the survey. Please reload this page or if problem persists, consider filling in the same survey form again."

    raw_response = json.loads(raw_response)

    email = get_user_by_uuid(uuid).data()['u']['uid']

    fields = {}
    for key, f in {f['key']: f for f in raw_response['data']['fields']}.items():
        if f['type'] in ['HIDDEN_FIELDS', 'INPUT_TEXT']:
            fields[f['label']] = escape_and_strip(f['value'])
        elif f['type'] in ['DROPDOWN', 'CHECKBOXES'] and 'options' in f:
            f['options'] = {o['id']: o['text'] for o in f['options']}
            fields[f['label']] = [escape_and_strip(f['options'][id]) for id in f['value']]
    fields.pop('uuid_encrypted')
    fields.pop('email')

    response = {
        'formId': raw_response['data']['formId'],
        'uuid': uuid,
        '@timestamp': raw_response['data']['createdAt'],
        'fields': fields
    }

    es_id = '_'.join([raw_response['data']['formId'], raw_response['data']['respondentId'], raw_response['data']['responseId']])

    if survey_form_key == 'user_info':
        first_name = response['fields'].get('first_name', '')
        last_name = response['fields'].get('last_name', '')
        if first_name == '' or last_name == '':
            raise Exception('Invalid response')

        # Save to ES and delete from Redis
        es_res = save_survey(es_id, response)
        if es_res['result'] not in ['created', 'noop']:
            raise Exception('Unable to save response')
        RedisQueries('cache').delete_cache('tally' + '_' + Globals.SURVEY_FORMS[survey_form_key], uuid)

        # Save names
        set_user_names(email, first_name, last_name)

        # Upgrade from Trial to Standard


        # return "Your account has been upgraded from Trial to Standard."
        return "Your response has been saved."


@profile_index_bp.route('/surveys/responses/list')
@login_required
def list_survey_responses():
    g.user = current_user

    return {
        'surveys': Globals.SURVEY_FORMS,
        'responses': [hit['_source'] for hit in get_survey_responses(g.user['uuid'])]
    }
