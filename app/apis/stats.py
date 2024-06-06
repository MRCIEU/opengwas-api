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
            'users': users
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
        for k, u in enumerate(mau):
            mau[k]['last_record'] = mau[k]['last_record']['hits']['hits'][0]['_source']
            emails.add(u['key'])
            ips.add(u['last_record']['ip'])

        users = get_user_by_emails(list(emails))
        geoip = get_geoip_using_pipeline(list(ips))

        for k, u in enumerate(mau):
            mau[k]['total_hours'] = round(u['sum_of_time']['value'] / 3600000, 2)
            mau[k]['source'] = Globals.USER_SOURCES[users[u['key']]['source']]
            mau[k]['location'] = geoip[u['last_record']['ip']]
            mau[k]['client'] = u['last_record']['source']
            email = u['key'].split('@')
            mau[k]['key'] = email[0][:4].ljust(len(email[0]), '*') + '@' + email[1]
            del mau[k]['last_record']

        return {
            'mau': mau
        }
