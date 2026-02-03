import flask
import jwt
import requests
import time

import airflow_client

from airflow_client.client import DagRunApi, TaskInstanceApi
from airflow_client.client.models.trigger_dag_run_post_body import TriggerDAGRunPostBody
from airflow_client.client.models.patch_task_instance_body import PatchTaskInstanceBody
from airflow_client.client.models.task_instance_state import TaskInstanceState
from werkzeug.exceptions import InternalServerError, Conflict

from .globals import Globals


def _check_airflow_jwt_validity() -> str:
    try:
        airflow_jwt = getattr(flask.g, 'airflow_jwt')
        exp = jwt.decode(airflow_jwt, options={"verify_signature": False, "verify_exp": True}).get("exp")
        if exp - time.time() <= 3600:  # Leaving an hour's buffer
            return ""
    except Exception:
        return ""
    return airflow_jwt


def _check_ang_get_airflow_jwt(url: str, username: str, password: str) -> str:
    airflow_jwt = _check_airflow_jwt_validity()
    if len(airflow_jwt) == 0:
        try:
            response = requests.post(f"{url}/auth/token",
                                     json={
                                         "username": username,
                                         "password": password
                                     })
            if response.status_code != 201:
                raise RuntimeError(f"Failed to get Airflow JWT: {response.status_code} {response.text}")
        except Exception as e:
            raise RuntimeError(f"Failed to get Airflow JWT: {str(e)}")
        flask.g.airflow_jwt = response.json()["access_token"]
        return flask.g.airflow_jwt
    return airflow_jwt


class Airflow:
    def __init__(self):
        airflow_url = 'http://' + Globals.app_config['airflow']['host'] + ':' + str(Globals.app_config['airflow']['port'])
        airflow_jwt = _check_ang_get_airflow_jwt(
            url=airflow_url,
            username=Globals.app_config['airflow']['username'],
            password=Globals.app_config['airflow']['password'],
        )
        configuration = airflow_client.client.Configuration(
            host=airflow_url,
            access_token=airflow_jwt,
        )
        self.api_client = airflow_client.client.ApiClient(configuration)
        self.task_description = {
            'test_files_on_oci': 'Looking for input files on storage',
            'create_instance': 'Creating compute instance',
            'download': 'Download files to the compute instance',
            'test_input_files': 'Looking for files on the compute instance',
            'gwas2vcf': 'Start: gwas2vcf',
            'test_vcf_files': 'Checking whether VCF files are ready',
            'clump': 'Start: clumping',
            'test_clump_file': 'Checking whether the clump file is ready',
            'ldsc': 'Start: LDSC',
            'test_ldsc_file': 'Checking whether the ldsc file is ready',
            'report': 'Start: Reporting',
            'test_report_files': 'Checking whether the report is ready',
            'delete_instance': 'Terminating the compute instance',
            'run_assoc': 'Start extracting and chunking associations',
            'test_assoc': 'Checking whether associations are ready',
            'run_phewas': 'Start extracting PheWAS and inserting to database',
            'test_phewas': 'Checking whether PheWAS records are ready',
            'run_tophits': 'Start extracting tophits and inserting to database',
            'test_tophits': 'Checking whether tophits are ready',
        }

    def trigger_dag_run(self, dag_id: str, dag_run_id: str, conf: dict):
        try:
            response = DagRunApi(self.api_client).trigger_dag_run(dag_id, TriggerDAGRunPostBody.from_dict({
                'conf': conf,
                'dag_run_id': dag_run_id,
            })).to_dict()
        except airflow_client.client.ApiException as e:
            if e.status == 409:
                raise Conflict("A pipeline for {} already exists".format(dag_run_id))
            raise InternalServerError("An error occurred when creating the pipeline: %s" % e)

        return {
            'dag_run_id': response['dag_run_id']
        }

    def get_dag_run(self, dag_id: str, dag_run_id: str, allow_not_found=False):
        try:
            response = DagRunApi(self.api_client).get_dag_run(dag_id, dag_run_id).to_dict()
        except airflow_client.client.ApiException as e:
            if e.status == 404 and allow_not_found:
                return {}
            raise InternalServerError("An error occurred retrieving the pipeline details: %s" % e)

        return {
            'dag_id': response['dag_id'],
            'dag_run_id': response['dag_run_id'],
            'state': response['state'].value if response['state'] else '',
            'start_date': response['start_date'].strftime('%Y-%m-%d %H:%M:%S %Z') if 'start_date' in response else '',
            'end_date': response['end_date'].strftime('%Y-%m-%d %H:%M:%S %Z') if 'end_date' in response else ''
        }

    def delete_dag_run(self, dag_id: str, dag_run_id: str):
        try:
            DagRunApi(self.api_client).delete_dag_run(dag_id, dag_run_id)
        except airflow_client.client.ApiException as e:
            if e.status != 404:
                raise InternalServerError("An error occurred when retrieving the pipeline details: %s" % e)

        validate = self.get_dag_run(dag_id, dag_run_id, allow_not_found=True)
        if validate == {}:
            return {}
        raise InternalServerError("An error occurred when deleting the pipeline")

    def get_task_instances(self, dag_id: str, dag_run_id: str, allow_not_found=False):
        try:
            response = TaskInstanceApi(self.api_client).get_task_instances(dag_id, dag_run_id).to_dict()

        except airflow_client.client.ApiException as e:
            if e.status == 404 and allow_not_found:
                response = {
                    'task_instances': [],
                }
            else:
                raise InternalServerError("An error occurred when retrieving the pipeline details: %s" % e)

        return {
            'dag_id': dag_id,
            'dag_run_id': dag_run_id,
            'tasks': {t['task_id']: t for t in sorted([{
                'task_id': t['task_id'],
                'priority': t['priority_weight'],
                'state': t['state'].value if 'state' in t else '',
                'start_date': t['start_date'].strftime('%Y-%m-%d %H:%M:%S %Z') if 'start_date' in t else '',
                'try_number': t['try_number'] if t['try_number'] else '',
                'end_date': t['end_date'].strftime('%Y-%m-%d %H:%M:%S %Z') if 'end_date' in t else '',
            } for t in response['task_instances']], key=lambda t: t.__getitem__('priority'), reverse=True)}
        }

    def patch_task_instances(self, dag_id: str, dag_run_id: str, task_id: str, new_state: str):
        try:
            TaskInstanceApi(self.api_client).patch_task_instance(dag_id, dag_run_id, task_id, PatchTaskInstanceBody.from_dict({
                'new_state': TaskInstanceState(new_state),
            }))
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
            if t['task_id'] not in ['delete_instance'] and t.get('state') not in ['success', 'upstream_failed', 'failed']:
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
