import time
from datetime import datetime

import airflow_client.client

from airflow_client.client.api import dag_run_api, task_instance_api
from airflow_client.client.model.dag_run import DAGRun
from airflow_client.client.model.update_task_instance import UpdateTaskInstance
from airflow_client.client.model.update_task_state import UpdateTaskState
from werkzeug.exceptions import InternalServerError, Conflict

from .globals import Globals


class Airflow:
    def __init__(self):
        configuration = airflow_client.client.Configuration(
            host='http://' + Globals.app_config['airflow']['host'] + ':' + str(Globals.app_config['airflow']['port']) + '/api/v1',
            username=Globals.app_config['airflow']['basic_auth_username'],
            password=Globals.app_config['airflow']['basic_auth_passwd']
        )
        self.api_client = airflow_client.client.ApiClient(configuration)
        self.task_description = {
            'test_files_on_oci': 'Check whether necessary files exist in storage',
            'create_instance': 'Create compute instance',
            'download': 'Start to download files to compute instance',
            'test_input_files': 'Check whether files are ready on compute instance',
            'gwas2vcf': 'Start gwas2vcf',
            'test_vcf_files': 'Check whether VCF files are ready',
            'clump': 'Start clump',
            'test_clump_file': 'Check whether clump file is ready',
            'ldsc': 'Start LDSC',
            'test_ldsc_file': 'Check whether ldsc file is ready',
            'report': 'Start report generation',
            'test_report_files': 'Check whether report files are ready',
            'delete_instance': 'Delete compute instance',
            'check_states': 'Check states of all tasks',
            'index': 'Start data transfer from files to database',
            'test_index_log': 'Check whether all data have been added to database'
        }

    @staticmethod
    def _convert_iso_date(isodate):
        return datetime.strftime(datetime.fromisoformat(isodate), '%Y-%m-%d %H:%M:%S %Z')

    def post_dag_run(self, dag_id: str, dag_run_id: str, conf: dict):
        try:
            response = dag_run_api.DAGRunApi(self.api_client).post_dag_run(dag_id, DAGRun(
                conf=conf,
                dag_run_id=dag_run_id
            ))
        except airflow_client.client.ApiException as e:
            if e.status == 409:
                raise Conflict("A pipeline for {} already exists".format(dag_run_id))
            raise InternalServerError("An error occurred when creating the pipeline: %s" % e)

        return {
            'dag_run_id': response['dag_run_id']
        }

    def get_dag_run(self, dag_id: str, dag_run_id: str, allow_not_found=False):
        try:
            response = dag_run_api.DAGRunApi(self.api_client).get_dag_run(dag_id, dag_run_id, fields=[
                'dag_id', 'dag_run_id', 'state', 'start_date', 'execution_date', 'end_date'
            ])
        except airflow_client.client.ApiException as e:
            if e.status == 404 and allow_not_found:
                return {}
            raise InternalServerError("An error occurred retrieving the pipeline details: %s" % e)

        return {
            'dag_id': response['dag_id'],
            'dag_run_id': response['dag_run_id'],
            'state': response['state']['value'] if response['state'] else '',
            'start_date': response['start_date'].strftime('%Y-%m-%d %H:%M:%S %Z') if response['start_date'] else '',
            'execution_date': response['execution_date'].strftime('%Y-%m-%d %H:%M:%S %Z') if response['execution_date'] else '',
            'end_date': response['end_date'].strftime('%Y-%m-%d %H:%M:%S %Z') if response['end_date'] else ''
        }

    def delete_dag_run(self, dag_id: str, dag_run_id: str):
        try:
            dag_run_api.DAGRunApi(self.api_client).delete_dag_run(dag_id, dag_run_id)
        except airflow_client.client.ApiException as e:
            if e.status != 404:
                raise InternalServerError("An error occurred when retrieving the pipeline details: %s" % e)

        validate = self.get_dag_run(dag_id, dag_run_id, allow_not_found=True)
        if validate == {}:
            return {}
        raise InternalServerError("An error occurred when deleting the pipeline")

    def get_task_instances(self, dag_id: str, dag_run_id: str):
        try:
            response = task_instance_api.TaskInstanceApi(self.api_client).get_task_instances(dag_id, dag_run_id)
        except airflow_client.client.ApiException as e:
            raise InternalServerError("An error occurred when retrieving the pipeline details: %s" % e)

        return {
            'dag_id': dag_id,
            'dag_run_id': dag_run_id,
            'tasks': {t['task_id']: t for t in sorted([{
                'task_id': t['task_id'],
                'priority': t['priority_weight'],
                'state': t['state']['value'] if t['state'] else '',
                'start_date': self._convert_iso_date(t['start_date']) if t['start_date'] else '',
                'try_number': t['try_number'] if t['try_number'] else '',
                'end_date': self._convert_iso_date(t['end_date']) if t['end_date'] else ''
            } for t in response['task_instances']], key=lambda t: t.__getitem__('priority'), reverse=True)}
        }

    def patch_task_instances(self, dag_id: str, dag_run_id: str, task_id: str, new_state: str):
        try:
            response = task_instance_api.TaskInstanceApi(self.api_client).patch_task_instance(dag_id, dag_run_id, task_id, UpdateTaskInstance(
                dry_run=False,
                new_state=UpdateTaskState(new_state))
            )
        except airflow_client.client.ApiException as e:
            raise InternalServerError("An error occurred when updating task instance state: %s" % e)

        return {
            'dag_id': dag_id,
            'dag_run_id': dag_run_id,
            'task_id': task_id
        }

    def fail_dag_run(self, dag_id: str, dag_run_id: str):
        tasks = self.get_task_instances(dag_id, dag_run_id)['tasks']
        if len(tasks) == 0:
            raise InternalServerError("No task instance found.")
        for _, t in tasks.items():
            # Look for the first substantial task that is still running
            if t['state'] not in ['success', 'upstream_failed', 'failed'] and t['task_id'] not in ['delete_instance', 'check_states']:
                return self.patch_task_instances(dag_id, dag_run_id, t['task_id'], 'failed')
        raise InternalServerError("It's too late to fail a DAG run. All substantial tasks have either succeeded or failed.")

    # Fail the first substantial remaining task of the given DAG run so that the compute instance can be terminated properly
    def fail_then_delete_dag_run(self, dag_id: str, dag_run_id: str, interval=10, n_retries=9):
        try:
            self.fail_dag_run(dag_id, dag_run_id)
        except InternalServerError as e:
            return {
                'dag_run_id': dag_run_id,
                'message': str(e)
            }

        for i in range(n_retries):
            if self.get_dag_run(dag_id, dag_run_id)['state'] in ['failed', 'success']:
                self.delete_dag_run(dag_id, dag_run_id)
                return {
                    'dag_run_id': dag_run_id
                }
            time.sleep(interval)
        raise InternalServerError("Timed out when waiting for tasks to fail.")
