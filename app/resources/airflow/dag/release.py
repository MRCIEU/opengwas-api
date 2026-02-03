import redis
import logging

from airflow import AirflowException
from airflow.sdk import dag
from airflow.providers.redis.hooks.redis import RedisHook
from airflow.providers.standard.operators.python import PythonOperator
from airflow.providers.standard.sensors.python import PythonSensor

import _utils


# logging.getLogger('oci').setLevel(logging.DEBUG)
# logging.basicConfig()


def _queue_task(redis_conn, action, **context) -> None:
    conf = context['dag_run'].conf

    redis_conn.sadd('tasks_pending', f"{conf['gwas_id_n']}:{conf['gwas_id']}:{action}")


def _test_task(redis_conn, action, **context) -> bool:
    conf = context['dag_run'].conf
    task = f"{conf['gwas_id_n']}:{conf['gwas_id']}:{action}"

    has_failed = redis_conn.hexists('tasks_failed', task)
    if has_failed:
        raise AirflowException(f"Task {task} failed")

    has_completed = redis_conn.hexists('tasks_completed', task)
    return True if has_completed else False


@dag(schedule=None, tags=['gwas'])
def release():
    redis_conn = RedisHook(redis_conn_id='redis_gwas_indexing').get_conn()

    timeouts = {
        'test_files': 30,
        'assoc': 14400,
        'phewas': 14400,
        'tophits': 14400,
    }

    test_files_on_oci = PythonSensor(
        task_id='test_files_on_oci',
        soft_fail=False,
        poke_interval=10,
        timeout=timeouts['test_files'],
        python_callable=_utils.test_files_on_oci_object_storage,
        op_args=[['{GWAS_ID}.vcf.gz', '{GWAS_ID}.vcf.gz.tbi']]
    )

    run_assoc = PythonOperator(
        task_id='run_assoc',
        python_callable=_queue_task,
        op_args=[redis_conn, 'assoc']
    )

    test_assoc = PythonSensor(
        task_id='test_assoc',
        soft_fail=False,
        poke_interval=10,
        mode='reschedule',
        timeout=timeouts['assoc'],
        python_callable=_test_task,
        op_args=[redis_conn, 'assoc']
    )

    run_phewas = PythonOperator(
        task_id='run_phewas',
        python_callable=_queue_task,
        op_args=[redis_conn, 'phewas']
    )

    test_phewas = PythonSensor(
        task_id='test_phewas',
        soft_fail=False,
        poke_interval=10,
        mode='reschedule',
        timeout=timeouts['phewas'],
        python_callable=_test_task,
        op_args=[redis_conn, 'phewas']
    )

    run_tophits = PythonOperator(
        task_id='run_tophits',
        python_callable=_queue_task,
        op_args=[redis_conn, 'tophits']
    )

    test_tophits = PythonSensor(
        task_id='test_tophits',
        soft_fail=False,
        poke_interval=10,
        mode='reschedule',
        timeout=timeouts['tophits'],
        python_callable=_test_task,
        op_args=[redis_conn, 'tophits']
    )

    test_files_on_oci >> run_assoc >> test_assoc >> run_phewas >> test_phewas >> run_tophits >> test_tophits


release()
