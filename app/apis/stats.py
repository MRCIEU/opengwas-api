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
            'by_source': users_count['by_source'],
            'by_group': users_count['by_group'],
            'has_valid_token': users_count['has_valid_token'],
            'online': RedisQueries("limiter").count_online_users()
        }

        gwasinfo = get_all_gwas_as_admin(['trait', 'group_name', 'category', 'subcategory'])
        for id, gi in gwasinfo.items():
            gwasinfo[id] = [gi['trait'], gi['group_name'], gi['category'], gi['subcategory']]

        return {
            'datasets': datasets,
            'users': users,
            'orgs': count_orgs(),
            'gwasinfo': gwasinfo,
            'user_sources': Globals.USER_SOURCES,
            'user_groups': Globals.USER_GROUPS
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

        mvd = json.loads(RedisQueries('cache').get_cache('stats_mvd', 'all' if field == '**' else field))
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

        mau = json.loads(RedisQueries('cache').get_cache('stats_mau', 'all' if field == '**' else field))
        # {'uuid': [reqs, time_ms, avg_n_datasets, ip, source], ...}

        ips = set()
        uuids = set()
        for id, stats in mau.items():
            uuids.add(id)
            ips.add(stats[3])

        users_and_orgs = get_user_by_uuids(list(uuids))
        geoip = get_geoip_using_pipeline(list(ips))

        mau_list = []
        org = {}
        stats_by_location = defaultdict(lambda: defaultdict(int))

        for uuids, stats in mau.items():
            uo = users_and_orgs[uuids]
            if uo['org'] is not None:
                org[uo['org']['uuid']] = uo['org']
            email = uo['user']['uid'].split('@')
            mau_list.append([
                # uid (masked)
                email[0][:4].ljust(len(email[0]), '*') + '@' + email[1],
                # reqs
                stats[0],
                # hours
                round(stats[1] / 3600000, 2),
                # avg_n_datasets
                stats[2],
                # source
                uo['user']['source'],
                # location
                geoip.get(stats[3], None),
                # client
                stats[4],
                # created
                uo['user'].get('created', None),
                # last_signin
                uo['user'].get('last_signin', None),
                # org_membership
                uo['org_membership'],
                # org_uuid
                uo['org']['uuid'] if uo['org'] is not None else None
            ])
            location = geoip.get(stats[3], '(?)')
            stats_by_location[location]['users'] += 1
            stats_by_location[location]['reqs'] += stats[0]
            stats_by_location[location]['ms'] += stats[1]

        for location, stats in stats_by_location.items():
            stats_by_location[location]['location'] = location
            stats_by_location[location]['hours'] = round(stats_by_location[location]['ms'] / 3600000)
            del stats_by_location[location]['ms']

        return {
            'mau': mau_list,
            'org': org,
            'stats_by_location': sorted(stats_by_location.values(), key=lambda l: l['users'], reverse=True)
        }
