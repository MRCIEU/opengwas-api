import airflow_client.client

from airflow_client.client.api import dag_run_api, task_instance_api
from airflow_client.client.model.dag_run import DAGRun
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

    def post_dag_run(self, dag_id: str, dag_run_id: str, conf: dict):
        try:
            response = dag_run_api.DAGRunApi(self.api_client).post_dag_run(dag_id, DAGRun(
                conf=conf,
                dag_run_id=dag_run_id
            ))
        except airflow_client.client.ApiException as e:
            if e.status == 409:
                raise Conflict("A pipeline for {} already exists".format(dag_run_id))
            raise InternalServerError("An error occurred when creating the pipeline %s" % e)

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
            raise InternalServerError("An error occurred retrieving the pipeline details %s" % e)

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
                raise InternalServerError("An error occurred retrieving the pipeline details %s" % e)

        validate = self.get_dag_run(dag_id, dag_run_id, allow_not_found=True)
        if validate == {}:
            return {}
        raise InternalServerError("An error occurred when deleting the pipeline")

    def get_task_instances(self, dag_id: str, dag_run_id: str):
        try:
            response = task_instance_api.TaskInstanceApi(self.api_client).get_task_instances(dag_id, dag_run_id)
        except airflow_client.client.ApiException as e:
            raise InternalServerError("An error occurred retrieving the pipeline details %s" % e)

        return {
            'dag_id': dag_id,
            'dag_run_id': dag_run_id,
            'tasks': {t['task_id']: t for t in sorted([{
                'task_id': t['task_id'],
                'priority': t['priority_weight'],
                'state': t['state']['value'] if t['state'] else '',
                'start_date': t['start_date'] if t['start_date'] else '',
                'try_number': t['try_number'] if t['try_number'] else '',
                'end_date': t['end_date'] if t['end_date'] else ''
            } for t in response['task_instances']], key=lambda t: t.__getitem__('priority'), reverse=True)}
        }
