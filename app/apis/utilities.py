from flask import make_response
from flask_restx import Resource, Namespace
import logging
import os
import json
import time
from collections import defaultdict

from queries.cql_queries import *
from queries.gwas_info_node import GwasInfo
from queries.redis_queries import RedisQueries
from resources.globals import Globals
from resources.neo4j import Neo4j
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
        skip_completed_tasks = False
        odds = 1

        n_skipped = 0
        if skip_completed_tasks:
            completed = RedisQueries('phewas_tasks', provider='webdis').get_completed_phewas_tasks()
        batches = defaultdict(int)
        for gi in Neo4j.get_db().run("MATCH (gi:GwasInfo) RETURN gi.id").data():
            batches['-'.join(gi['gi.id'].split('-', 2)[:2])] += 1
        samples = defaultdict(list)
        for batch, size in batches.items():
            for gi in Neo4j.get_db().run("MATCH (gi:GwasInfo) WHERE gi.id=~$batch RETURN gi.id, rand() as r ORDER BY r LIMIT $limit", batch=batch + ".*", limit=round(size * odds)).data():
                if skip_completed_tasks and gi['gi.id'] in completed:
                    n_skipped += 1
                else:
                    samples[batch].append(gi['gi.id'])
        samples_size = defaultdict(int)
        for batch, samples_in_batch in samples.items():
            samples_size[batch] = len(samples_in_batch)
            r = RedisQueries('phewas_tasks', provider='webdis').add_phewas_tasks(samples_in_batch)
            time.sleep(2)  # Avoid premature connection closure by webdis (bug?)

        return {
            'skipped': n_skipped,
            'batches': batches,
            'samples_size': samples_size,
            'samples': samples
        }


@api.route('/export_users')
@api.doc(description="Export users info")
class ExportUsers(Resource):
    def get(self):
        users = []
        for r in Neo4j.get_db().run("MATCH (u:User) WHERE u.source IS NOT NULL OPTIONAL MATCH (u)-[m]->(o:Org) RETURN u, o").data():
            uid = r['u']['uid'].split('@')
            u = [
                uid[0][:4].ljust(len(uid[0]), '*') + '@' + uid[1],
                r['u']['last_name'],
                Globals.USER_SOURCES[r['u']['source']],
                Globals.USER_TIERS[r['u'].get('tier', 'NONE')],
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

        result = "uid;last_name;source;tier;has_valid_jwt;org_uuid;org_name_microsoft;org_name_github\n"
        for u in users:
            result = result + ";".join(u) + "\n"

        response = make_response(result, 200)
        response.mimetype = "text/plain"
        return response
