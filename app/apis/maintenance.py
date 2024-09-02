import datetime

from flask_restx import Resource, Namespace
import logging
import json

from middleware.auth import key_required
from queries.cql_queries import *
from queries.es_admin import *
from queries.redis_queries import RedisQueries
from resources.airflow import Airflow
from resources.globals import Globals
from resources.oci import OCI


logger = logging.getLogger('debug-log')

api = Namespace('maintenance', description="Collection of maintenance endpoints")


def save_gwasinfo_cache():
    datasets = get_all_gwas_for_user(None)
    with open(Globals.STATIC_GWASINFO, 'w') as f:
        json.dump({
            'metadata': {
                'updated_at': datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H:%M:%S %Z'),
                'size': len(datasets)
            },
            'datasets': datasets
        }, f)
    with open(Globals.STATIC_GWASINFO, 'rb') as f:
        oci_upload = OCI().object_storage_upload('data', 'gwasinfo.json', f)
    return len(datasets)


@api.route('/gwasinfo/cache')
@api.doc(description="Update cache for default public GWAS info and update stats for all batches")
class CacheGwasInfo(Resource):
    parser = api.parser()

    @api.expect(parser)
    @api.doc(id='maintenance_gwasinfo_cache_get')
    @key_required
    def get(self):
        n = save_gwasinfo_cache()
        batches = update_batches_stats()
        return {
            'n_gwasinfo': n,
            'batches': batches
        }


@api.route('/pipeline/added_by_state/refresh')
@api.doc(description="Pull update ADDED_BY state for all datasets")
class RefreshAddedByStatus(Resource):
    parser = api.parser()

    @api.expect(parser)
    @api.doc(id='maintenance_pipeline_added_by_state_refresh_get')
    @key_required
    def get(self):
        gwas_id_and_state = get_added_by_state_of_all_draft_gwas()

        airflow = Airflow()

        for gwas_id, state in gwas_id_and_state.items():
            if state == 1 and airflow.get_dag_run('qc', gwas_id, True)['end_date'] != '':
                set_added_by_state_of_any_gwas(gwas_id, 2)
                gwas_id_and_state[gwas_id] = 2
            elif state == 4 and airflow.get_dag_run('release', gwas_id, True)['end_date'] != '':
                set_added_by_state_of_any_gwas(gwas_id, None)
                del gwas_id_and_state[gwas_id]

        return {
            'gwas_id_and_state': gwas_id_and_state
        }


@api.route('/stats/mvd/cache')
@api.doc(description="Update cache for dataset usage stats")
class CacheStatsMVD(Resource):
    parser = api.parser()
    parser.add_argument('year', required=False, type=str, default="*", help="Year of the time period of interest")
    parser.add_argument('month', required=False, type=str, choices=["*"] + [str(m).rjust(2, '0') for m in range(1, 13)], default="*", help="Month in the year of the time period of interest")

    @api.expect(parser)
    @api.doc(id='maintenance_stats_mvd_cache_get')
    @key_required
    def get(self):
        args = self.parser.parse_args()

        response = {
            'current_month': -1,
            'all': -1
        }

        def format_mvd(mvd):
            return [[
                mvd[i]['key'],
                mvd[i]['doc_count'],
                mvd[i]['group_by_uid']['value']
            ] for i, r in enumerate(mvd)]

        mvd = get_most_valued_datasets(args['year'], args['month'])
        result = format_mvd(mvd)
        if len(mvd) > 0:
            response['current_month'] = RedisQueries('stats').save_cache('stats_mvd', args['year'] + args['month'], json.dumps(result))

        mvd = get_most_valued_datasets('*', '*')
        result = format_mvd(mvd)
        if len(mvd) > 0:
            response['all'] = RedisQueries('stats').save_cache('stats_mvd', 'all', json.dumps(result))

        return response


@api.route('/stats/mau/cache')
@api.doc(description="Update cache for user activity stats")
class CacheStatsMAU(Resource):
    parser = api.parser()
    parser.add_argument('year', required=False, type=str, default="*", help="Year of the time period of interest")
    parser.add_argument('month', required=False, type=str, choices=["*"] + [str(m).rjust(2, '0') for m in range(1, 13)], default="*", help="Month in the year of the time period of interest")

    @api.expect(parser)
    @api.doc(id='maintenance_stats_mau_cache_get')
    @key_required
    def get(self):
        args = self.parser.parse_args()

        response = {
            'current_month': -1,
            'all': -1
        }

        def format_mau(mau):
            return [[
                mau[i]['key'],
                mau[i]['doc_count'],
                round(mau[i]['sum_of_time']['value']),
                round(mau[i]['stats_n_datasets']['avg'], 1),
                mau[i]['last_record']['hits']['hits'][0]['_source']['ip'],
                mau[i]['last_record']['hits']['hits'][0]['_source']['source']
            ] for i, r in enumerate(mau)]

        mau = get_most_active_users(args['year'], args['month'])
        result = format_mau(mau)
        if len(result) > 0:
            response['current_month'] = RedisQueries('stats').save_cache('stats_mau', args['year'] + args['month'], json.dumps(result))

        mau = get_most_active_users('*', '*')
        result = format_mau(mau)
        if len(result) > 0:
            response['all'] = RedisQueries('stats').save_cache('stats_mau', 'all', json.dumps(result))

        return response
