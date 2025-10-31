import requests
import logging

from airflow import AirflowException
from airflow.sdk import dag
from airflow.decorators import task
from airflow.operators.python import PythonOperator
from airflow.sensors.python import PythonSensor

import _oci
import _utils


# logging.getLogger('oci').setLevel(logging.DEBUG)
# logging.basicConfig()


def _task_create_instance(instance_client, **context) -> str:
    gwas_id = context['dag_run'].conf['gwas_id']

    existing_instances = _oci.list_instance(instance_client, gwas_id + '.release')
    for instance in existing_instances:
        if instance.lifecycle_state not in ['STOPPING', 'STOPPED', 'TERMINATING', 'TERMINATED']:
            raise AirflowException('An instance already exists for the same task. ' + instance.id)

    instance_ocid = _oci.launch_instance(instance_client, gwas_id + '.release')
    return instance_ocid


def _task_download(agent_client, timeout, **context):
    conf = context['dag_run'].conf
    instance_ocid = context['task_instance'].xcom_pull(key='return_value', task_ids='create_instance')

    command = _utils.wrap_command(
        {
            "ID": conf['gwas_id'],
            "URL": conf['url']
        },
        [
            "mkdir -p ~/work",
            "cd ~/work",
            "curl -O ${URL}${ID}/${ID}.vcf.gz -O ${URL}${ID}/clump.txt",
            "pwd && ls -l"
        ]
    )

    command_ocid = _oci.send_command_to_instance(agent_client, timeout, instance_ocid, command, conf['gwas_id'], 'download_vcf')
    return command_ocid


def _test_command_execution(agent_client, task_id, **context):
    instance_ocid = context['task_instance'].xcom_pull(key='return_value', task_ids='create_instance')
    command_ocid = context['task_instance'].xcom_pull(key='return_value', task_ids=task_id)
    execution = _oci.get_command_execution_result(agent_client, instance_ocid, command_ocid)

    return True if execution.lifecycle_state == 'SUCCEEDED' else False


def _task_index(agent_client, timeout, **context):
    conf = context['dag_run'].conf
    instance_ocid = context['task_instance'].xcom_pull(key='return_value', task_ids='create_instance')

    command = _utils.wrap_command(
        {
            "ID": conf['gwas_id'],
            "INDEX": conf['index'],
            "URL": conf['url'],
            "ES_HOST": conf['es_host'],
            "ES_PORT": conf['es_port']
        },
        [
            "source /opt/conda/etc/profile.d/conda.sh",
            "conda activate IGD-Elasticsearch",
            "cd ~/work",
            "python ~/IGD-elasticsearch/add-gwas.py -m index_data -f ${ID}.vcf.gz -g ${ID} -i ${INDEX} -e ${ES_HOST} -p ${ES_PORT} -t clump.txt",
            "conda deactivate"
        ]
    )

    command_ocid = _oci.send_command_to_instance(agent_client, timeout, instance_ocid, command, conf['gwas_id'], 'index')
    return command_ocid


def _test_index_log(**context):
    conf = context['dag_run'].conf
    r = requests.get(conf['url'] + conf['gwas_id'] + '/pipeline_output/index.log')
    print(r.text)
    if r.status_code == 200 and "All records indexed ok" in r.text and "All tophit records indexed ok" in r.text:
        return True
    return False


def _task_delete_instance(instance_client, **context):
    instance_ocid = context['task_instance'].xcom_pull(key='return_value', task_ids='create_instance')

    status = _oci.terminate_instance(instance_client, instance_ocid)

    if status != 204:
        raise AirflowException("Unable to terminate the instance")

    return True


@dag(schedule=None, tags=['gwas'])
def release():
    compute_instances_client = _oci.init_compute_instance_client()
    compute_instance_agent_client = _oci.init_compute_instance_agent_client()

    timeouts = {
        'test_files': 30,
        'command_poll': 300,
        'create_instance': 300,
        'download_files': 300,
        'index': 14400,
    }

    test_files_on_oci = PythonSensor(
        task_id='test_files_on_oci',
        soft_fail=False,
        poke_interval=10,
        timeout=timeouts['test_files'],
        python_callable=_utils.test_files_on_oci_object_storage,
        op_args=[['{GWAS_ID}.vcf.gz', 'clump.txt']]
    )

    create_instance = PythonOperator(
        task_id='create_instance',
        python_callable=_task_create_instance,
        op_args=[compute_instances_client]
    )

    download = PythonOperator(
        task_id='download',
        python_callable=_task_download,
        op_args=[compute_instance_agent_client, timeouts['download_files']]
    )

    test_input_files = PythonSensor(
        task_id='test_input_files',
        soft_fail=False,
        poke_interval=60,
        mode='reschedule',
        timeout=timeouts['command_poll'] + timeouts['create_instance'] + timeouts['download_files'],
        python_callable=_test_command_execution,
        op_args=[compute_instance_agent_client, 'download']
    )

    index = PythonOperator(
        task_id='index',
        python_callable=_task_index,
        op_args=[compute_instance_agent_client, timeouts['index']]
    )

    test_index_log = PythonSensor(
        task_id='test_index_log',
        soft_fail=False,
        poke_interval=60,
        timeout=timeouts['command_poll'] + timeouts['index'],
        mode='reschedule',
        python_callable=_test_index_log
    )

    delete_instance = PythonOperator(
        task_id='delete_instance',
        trigger_rule='none_skipped',  # Delete the instance even when upstream_failed (upstream will not fail until it times out)
        python_callable=_task_delete_instance,
        op_args=[compute_instances_client]
    )

    check_states = PythonSensor(
        task_id='check_states',
        trigger_rule='all_done',
        python_callable=_utils.check_states_of_all_tasks
    )

    test_files_on_oci >> create_instance >> download >> test_input_files >> index >> test_index_log >> delete_instance >> check_states


release()
