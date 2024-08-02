import requests


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
