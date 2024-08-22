import requests

from airflow import AirflowException


def _test_single_file_on_oci_object_storage(url, gwas_id, file_name) -> bool:
    r = requests.get(url + gwas_id + '/' + file_name)
    return True if r.status_code == 200 else False


def test_files_on_oci_object_storage(file_names, **context) -> bool:
    conf = context['dag_run'].conf
    return True if all([_test_single_file_on_oci_object_storage(conf['url'], conf['gwas_id'], file_name.replace("{GWAS_ID}", conf['gwas_id'])) for file_name in file_names]) else False


def wrap_command(envs: dict, core_command: list):
    full_command = ["export {}='{}'".format(k, v) for k, v in envs.items()]
    full_command.extend(["sudo -i -u opc bash << EOF"])
    full_command.extend(core_command)
    full_command.extend(["EOF"])
    return "\n".join(full_command)


def check_states_of_all_tasks(**context):
    for task_instance in context['dag_run'].get_task_instances():
        if task_instance.priority_weight >= context['task_instance'].priority_weight and task_instance.task_id != context['task_instance'].task_id and task_instance.current_state() != 'success':  # If any other task instance (except the current one) has failed
            raise AirflowException("This DAG run failed because task {} failed.".format(task_instance.task_id))
    return True
