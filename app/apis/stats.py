from flask_restx import Namespace, reqparse, Resource
import time

from middleware.auth import jwt_required, check_role
from queries.cql_queries import *
from queries.es_admin import *
from resources.globals import Globals
from queries.redis_queries import RedisQueries


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

        return {
            'datasets': datasets,
            'users': users,
            'orgs': count_orgs()
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

        mvd = get_most_valued_datasets(args['year'], args['month'])
        gwas_ids = []
        for k, d in enumerate(mvd):
            mvd[k]['group_by_uid'] = mvd[k]['group_by_uid']['value']
            gwas_ids.append(mvd[k]['key'])

        gwasinfo = get_gwas_as_admin(gwas_ids)

        return {
            'mvd': mvd,
            'gwasinfo': gwasinfo
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

        mau = get_most_active_users(args['year'], args['month'])
        ips = set()
        emails = set()
        for i, r in enumerate(mau):
            mau[i]['last_record'] = mau[i]['last_record']['hits']['hits'][0]['_source']
            emails.add(r['key'])
            ips.add(r['last_record']['ip'])

        users_and_orgs = get_user_by_emails(list(emails))
        geoip = get_geoip_using_pipeline(list(ips))

        org = {}

        for i, r in enumerate(mau):
            uo = users_and_orgs[r['key']]
            if uo['org'] is not None:
                org[uo['org']['uuid']] = uo['org']
            mau[i]['total_hours'] = round(r['sum_of_time']['value'] / 3600000, 2)
            mau[i]['stats_n_datasets'] = r['stats_n_datasets']
            mau[i]['source'] = Globals.USER_SOURCES[uo['user']['source']]
            mau[i]['location'] = geoip[r['last_record']['ip']]
            mau[i]['client'] = r['last_record']['source']
            mau[i]['created'] = uo['user']['created'] if 'created' in uo['user'] else None
            mau[i]['last_signin'] = uo['user']['last_signin'] if 'last_signin' in uo['user'] else None
            mau[i]['org_membership'] = uo['org_membership']
            mau[i]['org_uuid'] = uo['org']['uuid'] if uo['org'] is not None else None
            email = r['key'].split('@')
            mau[i]['key'] = email[0][:4].ljust(len(email[0]), '*') + '@' + email[1]
            del mau[i]['last_record']

        return {
            'mau': mau,
            'org': org
        }
