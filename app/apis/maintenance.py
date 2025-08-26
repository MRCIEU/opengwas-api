import gzip
import io
import json
import logging
import os
import pickle
import time

from flask import request
from flask_restx import Resource, Namespace

from middleware.auth import key_required
from queries.cql_queries import get_all_gwas_for_user, update_batches_stats, get_added_by_state_of_all_draft_gwas, set_added_by_state_of_any_gwas
from queries.es_stats import get_most_valued_datasets, get_most_active_users, get_recent_week_stats, get_past_hour_stats
from queries.redis_queries import RedisQueries
from resources import CryptographyTool
from resources.airflow import Airflow
from resources.globals import Globals
from resources._oci import OCIObjectStorage
from schemas.gwas_info_node_schema import valid_genome_build, valid_categories, valid_subcategories, valid_populations, valid_sex


logger = logging.getLogger('debug-log')

api = Namespace('maintenance', description="Collection of maintenance endpoints")


def save_gwasinfo_cache():  # This is the minimal dump of the public datasets
    datasets = get_all_gwas_for_user(None)

    datasets_compressed = {}
    removed_fields = ['id', 'group_name']
    reverse_coding = {
        'build': {v: i for i, v in enumerate(valid_genome_build)},
        'category': {v: i for i, v in enumerate(valid_categories)},
        'subcategory': {v: i for i, v in enumerate(valid_subcategories)},
        'population': {v: i for i, v in enumerate(valid_populations)},
        'sex': {v: i for i, v in enumerate(valid_sex)},
    }
    majority_fields_and_reverse_coding = {f: reverse_coding.get(f, {}) for f in ['trait', 'build', 'category', 'subcategory', 'population', 'sex', 'author', 'year', 'ontology', 'unit', 'sample_size', 'consortium', 'mr', 'priority']}
    majority_fields_and_coding = {f: list(rc.keys()) if len(rc) > 0 else [] for f, rc in majority_fields_and_reverse_coding.items()}

    for id in datasets.keys():
        gic = [[], {}]  # Compressed gwasinfo [[coded_values_of_majority_fields], {dict_of_other_fields}]
        for field in removed_fields:
            datasets[id].pop(field, None)
        for field, coding in majority_fields_and_reverse_coding.items():
            if len(coding) > 0:  # If field has coding
                value = datasets[id].pop(field, None)
                if value is not None:
                    gic[0].append(coding[value])
                else:
                    gic[0].append(None)
            else:
                gic[0].append(datasets[id].pop(field, None))
        gic[1] = datasets[id]
        datasets_compressed[id] = gic

    with open(Globals.STATIC_GWASINFO, 'w') as f:
        json.dump({
            'metadata': {
                'updated_at': int(time.time()),
                'size': len(datasets)
            },
            'majority_fields_and_coding': majority_fields_and_coding,
            'datasets_compressed': datasets_compressed
        }, f)
    with open(Globals.STATIC_GWASINFO, 'rb') as f:
        oci_upload = OCIObjectStorage().object_storage_upload('website', 'gwasinfo/gwasinfo.json', f)
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

        with open('/tmp/batches', 'w') as f:
            json.dump(batches, f)
        with open('/tmp/batches', 'rb') as f:
            oci_upload = OCIObjectStorage().object_storage_upload('website', 'gwasinfo/gwasinfo_batches.json', f)

        return {
            'n_gwasinfo': n,
            'batches': len(batches)
        }


@api.route('/associations/collect_indices')
@api.doc(description="Collect pos_prefix_indices for all datasets and merge into one")
class CacheGwasInfo(Resource):
    parser = api.parser()

    @api.expect(parser)
    @api.doc(id='maintenance_associations_collect_indices_get')
    @key_required
    def get(self):
        pos_prefix_indices = {}
        oci = OCIObjectStorage()
        output_path = f"{Globals.TMP_FOLDER}/0_pos_prefix_indices"

        for gwas_id, pos_prefix_index in RedisQueries('tasks', provider='ieu-db-proxy').get_gwas_pos_prefix_indices().items():
            pos_prefix_indices[gwas_id] = pickle.loads(pos_prefix_index)

        with gzip.open(output_path, 'wb') as f:
            pickle.dump(pos_prefix_indices, f)
        with open(output_path, 'rb') as f:
            oci.object_storage_upload('data-chunks', "0_pos_prefix_indices", f.read())
        os.remove(output_path)

        with gzip.GzipFile(
                fileobj=io.BytesIO(OCIObjectStorage().object_storage_download('data-chunks', '0_pos_prefix_indices').data.content),
                mode='rb') as f:
            pickle.loads(f.read())

        return {
            'n_datasets': len(pos_prefix_indices)
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
            return {mvd[i]['key']: [
                mvd[i]['doc_count'],
                mvd[i]['group_by_uuid']['value']
            ] for i in range(len(mvd))}

        mvd = get_most_valued_datasets(args['year'], args['month'])
        result = format_mvd(mvd)
        if len(mvd) > 0:
            response['current_month'] = RedisQueries('cache').save_cache('stats_mvd', args['year'] + args['month'], json.dumps(result))
            with open('/tmp/stats_mvd_current', 'w') as f:
                json.dump(result, f)
            with open('/tmp/stats_mvd_current', 'rb') as f:
                oci_upload = OCIObjectStorage().object_storage_upload('website', f"stats/mvd/{args['year']}{args['month']}.json", f)

        mvd = get_most_valued_datasets('*', '*')
        result = format_mvd(mvd)
        if len(mvd) > 0:
            response['all'] = RedisQueries('cache').save_cache('stats_mvd', 'all', json.dumps(result))
            with open('/tmp/stats_mvd_all', 'w') as f:
                json.dump(result, f)
            with open('/tmp/stats_mvd_all', 'rb') as f:
                oci_upload = OCIObjectStorage().object_storage_upload('website', 'stats/mvd/all.json', f)

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
            return {mau[i]['key']: [
                mau[i]['doc_count'],
                round(mau[i]['sum_of_time']['value']),
                round(mau[i]['stats_n_datasets']['avg'], 1),
                mau[i]['last_record']['hits']['hits'][0]['_source']['ip'],
                mau[i]['last_record']['hits']['hits'][0]['_source']['source']
            ] for i in range(len(mau))}

        mau = get_most_active_users(args['year'], args['month'])
        result = format_mau(mau)
        if len(result) > 0:
            response['current_month'] = RedisQueries('cache').save_cache('stats_mau', args['year'] + args['month'], json.dumps(result))
            with open('/tmp/stats_mau_current', 'w') as f:
                json.dump(result, f)
            with open('/tmp/stats_mau_current', 'rb') as f:
                oci_upload = OCIObjectStorage().object_storage_upload('website', f"stats/mau/{args['year']}{args['month']}.json", f)

        mau = get_most_active_users('*', '*')
        result = format_mau(mau)
        if len(result) > 0:
            response['all'] = RedisQueries('cache').save_cache('stats_mau', 'all', json.dumps(result))
            with open('/tmp/stats_mau_all', 'w') as f:
                json.dump(result, f)
            with open('/tmp/stats_mau_all', 'rb') as f:
                oci_upload = OCIObjectStorage().object_storage_upload('website', 'stats/mau/all.json', f)

        return response


@api.route('/stats/recent_week/cache')
@api.doc(description="Update cache for per hour stats of the past week")
class CacheStatsRecentWeek(Resource):
    @api.doc(id='maintenance_stats_recent_week_cache_get')
    @key_required
    def get(self):
        recent_week = get_recent_week_stats()
        recent_week = dict(sorted({hour['key_as_string']: [
            hour['doc_count'],  # Number of requests
            int(hour['records']['value']),  # Number of records returned
            hour['users']['value'],  # Number of unique users
            round(hour['time']['value'] / 1000 / 3600, 2),  # Load
            round(hour['time_pct']['values']['90.0']),  # 90th percentile of response time
            round(hour['slow_reqs']['doc_count'] / hour['doc_count'], 2),  # Fraction of slow requests
        ] for hour in recent_week}.items()))
        recent_week.popitem()  # Remove current hour which is incomplete

        with open('/tmp/stats_recent_week', 'w') as f:
            json.dump(recent_week, f)
        with open('/tmp/stats_recent_week', 'rb') as f:
            oci_upload = OCIObjectStorage().object_storage_upload('website', 'stats/recent_week.json', f)

        return {
            'latest_hour': int(list(recent_week.keys())[-1])
        }


@api.route('/stats/past_hour')
@api.doc(description="Get stats for the past hour")
class CacheStatsPastHour(Resource):
    @api.doc(id='maintenance_stats_past_hour_get')
    @key_required
    def get(self):
        past_hour = get_past_hour_stats()
        past_hour = dict({endpoint['key']: [
            endpoint['doc_count'],  # Number of requests
            int(endpoint['records']['value']),  # Number of records returned
            round(endpoint['time']['value'] / 1000, 2),  # Total processing time
            round(endpoint['time_pct']['values']['90.0']),  # 90th percentile of response time
            round(endpoint['slow_reqs']['doc_count'] / endpoint['doc_count'], 2),  # Fraction of slow requests
        ] for endpoint in past_hour}.items())

        return {
            'metadata': {
                'updated_at': int(time.time()),
            },
            'past_hour': past_hour,
        }


@api.route('/survey/save')
@api.doc(description="Save responses pushed by tally")
class SaveTallyResponse(Resource):
    parser = api.parser()

    @api.expect(parser)
    @api.doc(id='maintenance_survey_save_post')
    @key_required
    def post(self):
        payload = request.json

        uuid = ''
        for f in payload['data']['fields']:
            if f['label'] == 'uuid_encrypted':
                uuid = CryptographyTool().decrypt(f['value'])

        if uuid != '':
            return RedisQueries('cache').save_cache('tally' + '_' + payload['data']['formId'], uuid, json.dumps(payload))

        return 0
