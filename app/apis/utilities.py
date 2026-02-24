import shortuuid

from flask import make_response
from flask_restx import Resource, Namespace
import json
import logging
import os
import random
import time
from collections import defaultdict
from pprint import pprint

from queries.cql_queries import *
from queries.gwas_info_node import GwasInfo
from queries.redis_queries import RedisQueries
from resources.globals import Globals
from resources.neo4j import Neo4j
from resources.airflow import Airflow
from schemas.gwas_info_node_schema import GwasInfoNodeSchema


logger = logging.getLogger('debug-log')

api = Namespace('utilities', description="Utilities for uncommon operations")
gwas_info_model = api.model('GwasInfo', GwasInfoNodeSchema.get_flask_model())


def get_neo4j_stats(tx):
    return {
        'COUNT(n)': tx.run("MATCH (n) RETURN COUNT(n);").single()['COUNT(n)'],
        'COUNT(r)': tx.run("MATCH ()-[r]->() RETURN COUNT(r);").single()['COUNT(r)'],
        'COUNT(n:GwasInfo)': tx.run("MATCH (n:GwasInfo) RETURN COUNT(n);").single()['COUNT(n)'],
        'COUNT(r:DID_QC)': tx.run("MATCH ()-[r:DID_QC]->() RETURN COUNT(r);").single()['COUNT(r)'],
    }


@api.route('/import_metadata_from_json')
@api.doc(description="Import metadata from JSON files collected from batch imported datasets, and set QC as passed")
class ImportMetadataFromJSON(Resource):
    parser = api.parser()
    parser.add_argument('overwrite', type=str, required=False, help="Whether to overwrite existing GwasInfo and update DID_QC")

    developer_uid = ''  # Specify the email address of the developer
    working_dir = ''  # A json/ subdirectory of this directory has all the .json files
    gwas_info_fields = GwasInfoNodeSchema.get_flask_model().keys()

    def get(self):
        req = self.parser.parse_args()
        metadata_batch = {}
        stats = {'before': {}, 'midway': {}, 'after': {}}
        results = {'created': {}, 'skipped': {}, 'edited': {}, 'error': {}}

        for filename in os.listdir(os.path.join(self.working_dir, 'json')):
            gwas_id = filename.split('.')[0]
            with open(os.path.join(self.working_dir, 'json', gwas_id + '.json')) as metadata_json:
                metadata_batch[gwas_id] = {field: value for field, value in json.load(metadata_json).items() if field in self.gwas_info_fields}
                for field in ['category', 'subcategory', 'sex']:
                    if field not in metadata_batch[gwas_id]:
                        metadata_batch[gwas_id][field] = 'NA'
                if metadata_batch[gwas_id]['population'] == 'NR':
                    metadata_batch[gwas_id]['population'] = 'NA'
        print(len(metadata_batch))

        tx = Neo4j.get_db()
        stats['before'] = get_neo4j_stats(tx)
        i = 1

        for gwas_id, metadata in metadata_batch.items():
            try:  # Add GwasInfo node and DID_QC relationship
                add_new_gwas(self.developer_uid, metadata, {'public'}, gwas_id)
                add_quality_control(self.developer_uid, gwas_id, data_passed=True)
                results['created'][gwas_id] = ['', json.dumps(metadata)]
                print(i, gwas_id, 'created')
                i += 1
            except ValueError:  # If GwasInfo exists for gwas_id
                result = tx.run(
                    "MATCH (gi:GwasInfo {id: $gwas_id}) RETURN gi;",
                    gwas_id=gwas_id
                ).single()
                existing_gwas_info = GwasInfoNodeSchema().load(GwasInfo(result['gi']))
                results['skipped'][gwas_id] = [json.dumps(existing_gwas_info), '']
            except Exception as e:
                results['error'][gwas_id] = ['add', str(e)]
                print(i, gwas_id, 'error')
                i += 1

        stats['midway'] = get_neo4j_stats(tx)

        if 'overwrite' in req and req['overwrite'] == '1':
            for gwas_id, result in results['skipped'].items():
                try:  # Update existing GwasInfo node and DID_QC relationship
                    # These methods do not require developer access
                    edit_existing_gwas(gwas_id, metadata_batch[gwas_id])
                    delete_quality_control(gwas_id)  # Must delete first as DID_QC by another developer will pass uniqueness validation
                    add_quality_control(self.developer_uid, gwas_id, data_passed=True)
                    results['edited'][gwas_id] = [result[0], json.dumps(metadata_batch[gwas_id])]
                    print(i, gwas_id, 'edited')
                    i += 1
                except Exception as e:
                    results['error'][gwas_id] = ['edit', str(e)]
                    print(i, gwas_id, 'error')
                    i += 1
            results['skipped'] = {}

            stats['after'] = get_neo4j_stats(tx)

        with open(os.path.join(self.working_dir, 'results_' + time.strftime("%Y%m%d_%H%M%S", time.localtime()) + '.txt'), 'w') as result_csv:
            for outcome in results.keys():
                for gwas_id, result in results[outcome].items():
                    result_csv.write(f'{outcome}|{gwas_id}|{",".join(result)}\n')

        return {
            'outcome': {outcome: len(results[outcome]) for outcome in results},
            'stats': stats
        }, 200


@api.route('/sample_datasets')
@api.doc(description="Sample from datasets across all batches using the odds specified, and add to the pending tasks list in Redis")
class SampleDatasetsByBatches(Resource):
    def get(self):
        # Settings
        skip_completed_tasks = True
        odds = 1
        action = 'assoc'

        n_skipped = 0
        if skip_completed_tasks:
            completed = RedisQueries('indexing').get_completed_tasks()
        tasks_by_batch = defaultdict(list)
        for ids in Neo4j.get_db().run("MATCH (n:GwasInfo) WHERE EXISTS {MATCH (n:GwasInfo)-[r:DID_QC]->(u:User)} RETURN n.id AS gwas_id, id(n) AS id_n"):
            tasks_by_batch['-'.join(ids['gwas_id'].split('-', 2)[:2])].append(f"{ids['id_n']}:{ids['gwas_id']}:{action}")
        samples = defaultdict(list)
        for batch, ids in tasks_by_batch.items():
            if batch not in ['eqtl-a']:
                continue
            for task in random.sample(ids, round(len(tasks_by_batch[batch]) * odds)):
                if skip_completed_tasks and task in completed:
                    n_skipped += 1
                else:
                    samples[batch].append(task)
        samples_size = defaultdict(int)
        for batch, samples_in_batch in samples.items():
            samples_size[batch] = len(samples_in_batch)
            r = RedisQueries('indexing').add_tasks(samples_in_batch)

        return {
            'skipped': n_skipped,
            'batches': list(tasks_by_batch.keys()),
            'samples_size': samples_size,
            'samples': samples
        }


@api.route('/export_users')
@api.doc(description="Export list of users")
class ExportUsers(Resource):
    def get(self):
        users = []
        for r in Neo4j.get_db().run("MATCH (u:User) WHERE u.source IS NOT NULL OPTIONAL MATCH (u)-[m]->(o:Org) RETURN u, o").data():
            uid = r['u']['uid'].split('@')
            u = [
                uid[0][:4].ljust(len(uid[0]), '*') + '@' + uid[1],
                r['u']['last_name'],
                Globals.USER_SOURCES[r['u']['source']],
                Globals.USER_GROUPS[r['u'].get('group', 'NONE')],
                "1" if (r['u'].get('jwt_timestamp', 0) + Globals.JWT_VALIDITY - time.time()) > 0 else "0"
            ]
            if r['o']:
                u.extend([
                    r['o']['uuid'],
                    r['o'].get('ms_name', ""),
                    r['o'].get('gh_name', "")
                ])
            else:
                u.extend(["", "", ""])
            users.append(u)

        result = "uid;last_name;source;group;has_valid_jwt;org_uuid;org_name_microsoft;org_name_github\n"
        for u in users:
            result = result + ";".join(u) + "\n"

        response = make_response(result, 200)
        response.mimetype = "text/plain"
        return response


# @api.route('/init_user_uuid')
# @api.doc(description="Initialise uuid for users")
# class InitUUIDForUsers(Resource):
#     def get(self):
#         tx = Neo4j.get_db()
#         uids = tx.run("MATCH (u:User) RETURN COLLECT(u.uid)").single()[0]
#         data = []
#         for uid in uids:
#             data.append({
#                 'uid': uid,
#                 'uuid': shortuuid.uuid()
#             })
#         tx.run("UNWIND $data AS p MATCH (u:User) WHERE u.uid = p.uid SET u.uuid = p.uuid", data=data)
#         return data


@api.route('/list_user_uuid')
@api.doc(description="List uuid of users")
class ListUUIDOfUsers(Resource):
    def get(self):
        uuids = {}
        for r in Neo4j.get_db().run("MATCH (u:User) WHERE u.uuid IS NOT NULL RETURN u").data():
            uuids[r['u']['uid']] = r['u']['uuid']
        return {
            'uuids': uuids
        }


@api.route('/test_airflow')
@api.doc(description="Test airflow")
class TestAirflow(Resource):
    def get(self):
        airflow = Airflow()

        airflow = airflow.get_dag_run('release', 'ieu-b-5137', True)

        return airflow
