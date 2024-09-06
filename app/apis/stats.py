import json
from collections import defaultdict

from flask_restx import Namespace, reqparse, Resource
import time

from .edit import check_batch_exists
from middleware.auth import jwt_required, check_role
from queries.cql_queries import *
from queries.es_admin import *
from queries.redis_queries import RedisQueries
from resources.globals import Globals


api = Namespace('stats', description="Get statistics from logs")


@api.route('/overall')
@api.hide
# Get the overall stats of datasets and users
class Overall(Resource):
    @api.doc(id='mvd_get', security=['token_jwt'])
    @jwt_required
    @check_role('admin')
    def get(self):
        gwasinfo_group_count = count_gwas_by_group()
        datasets = {
            "public": gwasinfo_group_count['public'],
            "private": 0
        }
        del gwasinfo_group_count['public']
        datasets['private'] = sum(gwasinfo_group_count.values())

        users_count = count_users(int(time.time()) - Globals.JWT_VALIDITY)
        users = {
            'all': sum(users_count['by_source'].values()),
            'by_source': {Globals.USER_SOURCES[k]: v for k, v in users_count['by_source'].items()},
            'by_tier': {Globals.USER_TIERS[k]: v for k, v in users_count['by_tier'].items()},
            'has_valid_token': users_count['has_valid_token'],
            'online': RedisQueries("limiter").count_online_users()
        }

        gwasinfo = get_all_gwas_as_admin(['trait', 'group_name', 'category', 'subcategory'])
        for id, gi in gwasinfo.items():
            gwasinfo[id] = [gi['trait'], gi['group_name'], gi['category'], gi['subcategory']]

        return {
            'datasets': datasets,
            'users': users,
            'orgs': count_orgs()
            'orgs': count_orgs(),
            'gwasinfo': gwasinfo
        }


@api.route('/mvd')
@api.hide
# Get the list of most valued datasets
class MostValuedDatasets(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('year', required=False, type=str, default="*", help="Year of the time period of interest")
    parser.add_argument('month', required=False, type=str, choices=["*"] + [str(m).rjust(2, '0') for m in range(1, 13)], default="*", help="Month in the year of the time period of interest")

    @api.expect(parser)
    @api.doc(id='mvd_get', security=['token_jwt'])
    @jwt_required
    @check_role('admin')
    def get(self):
        args = self.parser.parse_args()

        field = args['year'] + args['month']

        mvd = json.loads(RedisQueries('stats').get_cache('stats_mvd', 'all' if field == '**' else field))
        # {'id': [reqs, users], ...}

        stats_by_batch = defaultdict(lambda: defaultdict(int))
        for b in get_batches():
            stats_by_batch[b['id']].update(b)
        for id, stats in mvd.items():
            batch = check_batch_exists(id, Globals.all_batches)
            stats_by_batch[batch]['used'] += 1
            stats_by_batch[batch]['reqs'] += stats[0]

        return {
            'mvd': mvd,
            'stats_by_batch': sorted(stats_by_batch.values(), key=lambda l: l['reqs'], reverse=True)
        }


@api.route('/mau')
@api.hide
# Get the list of most active users
class MostValuedUsers(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('year', required=False, type=str, default="*", help="Year of the time period of interest")
    parser.add_argument('month', required=False, type=str, choices=["*"] + [str(m).rjust(2, '0') for m in range(1, 13)], default="*", help="Month in the year of the time period of interest")

    @api.expect(parser)
    @api.doc(id='mau_get', security=['token_jwt'])
    @jwt_required
    @check_role('admin')
    def get(self):
        args = self.parser.parse_args()

        field = args['year'] + args['month']

        mau = json.loads(RedisQueries('stats').get_cache('stats_mau', 'all' if field == '**' else field))
        ips = set()
        emails = set()
        for u in mau:
            emails.add(u[0])
            ips.add(u[4])

        users_and_orgs = get_user_by_emails(list(emails))
        geoip = get_geoip_using_pipeline(list(ips))

        mau_list_of_dict = []
        org = {}
        stats_by_location = defaultdict(lambda: defaultdict(int))

        for i, r in enumerate(mau):
            uo = users_and_orgs[r[0]]
            if uo['org'] is not None:
                org[uo['org']['uuid']] = uo['org']
            email = r[0].split('@')
            u = {
                'key': email[0][:4].ljust(len(email[0]), '*') + '@' + email[1],
                'reqs': r[1],
                'hours': round(r[2] / 3600000, 2),
                'avg_n_datasets': r[3],
                'source': Globals.USER_SOURCES[uo['user']['source']],
                'location': geoip.get(r[4], None),
                'client': r[5],
                'created': uo['user'].get('created', None),
                'last_signin': uo['user'].get('last_signin', None),
                'org_membership': uo['org_membership'],
                'org_uuid': uo['org']['uuid'] if uo['org'] is not None else None
            }
            mau_list_of_dict.append(u)
            location = geoip.get(r[4], '(?)')
            stats_by_location[location]['users'] += 1
            stats_by_location[location]['reqs'] += r[1]
            stats_by_location[location]['ms'] += r[2]

        for location, stats in stats_by_location.items():
            stats_by_location[location]['location'] = location
            stats_by_location[location]['hours'] = round(stats_by_location[location]['ms'] / 3600000)
            del stats_by_location[location]['ms']

        return {
            'mau': mau_list_of_dict,
            'org': org,
            'stats_by_location': sorted(stats_by_location.values(), key=lambda l: l['users'], reverse=True)
        }
