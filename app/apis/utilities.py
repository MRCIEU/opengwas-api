from flask_restplus import Resource, Namespace
from queries.cql_queries import *
from queries.gwas_info_node import GwasInfo
import logging
import os
import json
import time

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

    developer_uid = ''
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
