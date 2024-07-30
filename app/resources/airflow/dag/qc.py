from airflow import AirflowException
from airflow.decorators import dag, task
from airflow.models import Variable
from airflow.operators.python import PythonOperator
from airflow.sensors.python import PythonSensor

import requests
import oci
import logging
from hashlib import sha256


# logging.getLogger('oci').setLevel(logging.DEBUG)
# logging.basicConfig()


def _oci_init_config() -> dict:
    config = {
        "user": Variable.get("OCI_USER_OCID"),
        "fingerprint": Variable.get("OCI_KEY_FINGERPRINT"),
        "tenancy": Variable.get("OCI_TENANCY"),
        "region": Variable.get("OCI_REGION"),
        "key_content": Variable.get("SECRET_OCI_KEY"),
        "log_requests": True
    }
    oci.config.validate_config(config)
    return config


def _oci_init_compute_instance_client() -> oci.core.ComputeClient:
    return oci.core.ComputeClient(_oci_init_config())


def _oci_init_compute_instance_agent_client() -> oci.compute_instance_agent.ComputeInstanceAgentClient:
    return oci.compute_instance_agent.ComputeInstanceAgentClient(_oci_init_config())


def _oci_launch_instance(instance_client, display_name) -> str:
    launch_instance_response = instance_client.launch_instance(
        launch_instance_details=oci.core.models.LaunchInstanceDetails(
            availability_domain="ZJqB:UK-LONDON-1-AD-2",
            compartment_id=Variable.get('OCI_COMPARTMENT_ID'),
            create_vnic_details=oci.core.models.CreateVnicDetails(
                subnet_id=Variable.get('OCI_SUBNET_ID')),
            display_name=display_name,
            availability_config=oci.core.models.LaunchInstanceAvailabilityConfigDetails(
                is_live_migration_preferred=True,
                recovery_action="STOP_INSTANCE"),
            metadata={
                'ssh_authorized_keys': Variable.get('OCI_SSH_PUBLIC_KEY')},
            shape="VM.Standard.E5.Flex",
            shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(
                ocpus=1,
                memory_in_gbs=8),
            source_details=oci.core.models.InstanceSourceViaImageDetails(
                source_type="image",
                boot_volume_size_in_gbs=55,
                image_id=Variable.get('OCI_IMAGE_ID')),
        ),
    )

    print(launch_instance_response.data)
    return launch_instance_response.data.id


def _oci_list_instance(instance_client, display_name):
    list_instances_response = instance_client.list_instances(
        compartment_id=Variable.get('OCI_COMPARTMENT_ID'),
        display_name=display_name,
        limit=50,
        sort_by="TIMECREATED",
        sort_order="ASC")

    print(list_instances_response.data)
    return list_instances_response.data


def _oci_send_command_to_instance(agent_client, timeout, instance_ocid, command, gwas_id, display_name):
    create_instance_agent_command_response = agent_client.create_instance_agent_command(
        create_instance_agent_command_details=oci.compute_instance_agent.models.CreateInstanceAgentCommandDetails(
            compartment_id=Variable.get('OCI_COMPARTMENT_ID'),
            execution_time_out_in_seconds=timeout,
            target=oci.compute_instance_agent.models.InstanceAgentCommandTarget(
                instance_id=instance_ocid),
            content=oci.compute_instance_agent.models.InstanceAgentCommandContent(
                source=oci.compute_instance_agent.models.InstanceAgentCommandSourceViaTextDetails(
                    source_type="TEXT",
                    text=command,
                    text_sha256=sha256(command.encode('utf-8')).hexdigest()),
                output=oci.compute_instance_agent.models.InstanceAgentCommandOutputViaObjectStorageTupleDetails(
                    output_type="OBJECT_STORAGE_TUPLE",
                    bucket_name="upload",
                    namespace_name="ieup4",
                    object_name=('{}/pipeline_output/{}.log'.format(gwas_id, display_name)))),
            display_name=display_name)
    )

    print(command)
    print(create_instance_agent_command_response.data)
    return create_instance_agent_command_response.data.id


def _oci_get_command_execution_result(agent_client, instance_ocid, command_ocid):
    get_instance_agent_command_execution_response = agent_client.get_instance_agent_command_execution(
        instance_agent_command_id=command_ocid,
        instance_id=instance_ocid)

    print(get_instance_agent_command_execution_response.data)
    return get_instance_agent_command_execution_response.data


def _oci_terminate_instance(instance_client, instance_ocid):
    terminate_instance_response = instance_client.terminate_instance(
        instance_id=instance_ocid,
        preserve_boot_volume=False,
        preserve_data_volumes_created_at_launch=False)

    print(terminate_instance_response.headers)
    return terminate_instance_response.status


def _task_create_instance(instance_client, **context) -> str:
    gwas_id = context['dag_run'].conf['gwas_id']

    existing_instances = _oci_list_instance(instance_client, gwas_id)
    for instance in existing_instances:
        if instance.lifecycle_state not in ['STOPPING', 'STOPPED', 'TERMINATING', 'TERMINATED']:
            raise AirflowException('An instance already exists for the same task. ' + instance.id)

    instance_ocid = _oci_launch_instance(instance_client, gwas_id)
    return instance_ocid


def _test_single_file_on_oci_object_storage(par_upload, gwas_id, file_name) -> bool:
    r = requests.get(par_upload + gwas_id + '/' + file_name)
    return True if r.status_code == 200 else False


def _test_files_on_oci_object_storage(file_names, **context) -> bool:
    conf = context['dag_run'].conf
    return True if all([_test_single_file_on_oci_object_storage(conf['url'], conf['gwas_id'], file_name.replace("{GWAS_ID}", conf['gwas_id'])) for file_name in file_names]) else False


def _wrap_command(gwas_id, url, core_command: list):
    full_command = [
        "export ID='{}'".format(gwas_id),
        "export URL='{}'".format(url),
        "sudo -i -u opc bash << EOF"
    ]
    full_command.extend(core_command)
    full_command.extend(["EOF"])
    return "\n".join(full_command)


def _task_download(agent_client, timeout, **context):
    gwas_id = context['dag_run'].conf['gwas_id']
    instance_ocid = context['task_instance'].xcom_pull(key='return_value', task_ids='create_instance')

    command = _wrap_command(
        gwas_id,
        Variable.get('SECRET_OCI_PAR_URL_UPLOAD'),
        [
            "mkdir -p ~/work",
            "cd ~/work",
            "curl -O ${URL}${ID}/upload.txt.gz -O ${URL}${ID}/${ID}_data.json -O ${URL}${ID}/${ID}.json",
            "pwd && ls -l"
        ]
    )

    command_ocid = _oci_send_command_to_instance(agent_client, timeout, instance_ocid, command, gwas_id, 'download')
    return command_ocid


def _test_command_execution(agent_client, task_id, **context):
    instance_ocid = context['task_instance'].xcom_pull(key='return_value', task_ids='create_instance')
    command_ocid = context['task_instance'].xcom_pull(key='return_value', task_ids=task_id)
    execution = _oci_get_command_execution_result(agent_client, instance_ocid, command_ocid)

    return True if execution.lifecycle_state == 'SUCCEEDED' else False


def _task_gwas2vcf(agent_client, timeout, **context):
    conf = context['dag_run'].conf
    instance_ocid = context['task_instance'].xcom_pull(key='return_value', task_ids='create_instance')

    command = _wrap_command(
        conf['gwas_id'],
        conf['url'],
        [
            "source /opt/conda/etc/profile.d/conda.sh",
            "conda activate gwas2vcf",
            "cd ~/work",
            "python ../gwas2vcf/main.py --id ${ID} --json ${ID}_data.json --data upload.txt.gz --out ./${ID}.vcf.gz --ref ~/ref/reference_genomes/human_g1k_v37.fasta --dbsnp ~/ref/dbsnp/dbsnp.v153.b37.vcf.gz --alias ~/gwas2vcf/alias-b37.txt",
            "conda deactivate",
            "curl -X PUT --data-binary '@${ID}.vcf.gz' ${URL}${ID}/${ID}.vcf.gz",
            "curl -X PUT --data-binary '@${ID}.vcf.gz.tbi' ${URL}${ID}/${ID}.vcf.gz.tbi"
        ]
    )

    command_ocid = _oci_send_command_to_instance(agent_client, timeout, instance_ocid, command, conf['gwas_id'], 'gwas2vcf')
    return command_ocid


def _task_clump(agent_client, timeout, **context):
    conf = context['dag_run'].conf
    instance_ocid = context['task_instance'].xcom_pull(key='return_value', task_ids='create_instance')

    command = _wrap_command(
        conf['gwas_id'],
        conf['url'],
        [
            "source /opt/conda/etc/profile.d/conda.sh",
            "conda activate ldsc",
            "cd ~/work",
            "python ~/gwas_processing/clump.py --bcf ./${ID}.vcf.gz --out clump.txt --bcftools_binary ~/tools/bcftools/bcftools --plink_binary ~/tools/plink --plink_ref ~/ref/ld_files/data_maf0.01_rs",
            "conda deactivate",
            "curl -X PUT --data-binary '@clump.txt' ${URL}${ID}/clump.txt",
        ]
    )

    command_ocid = _oci_send_command_to_instance(agent_client, timeout, instance_ocid, command, conf['gwas_id'], 'clump')
    return command_ocid


def _task_ldsc(agent_client, timeout, **context):
    conf = context['dag_run'].conf
    instance_ocid = context['task_instance'].xcom_pull(key='return_value', task_ids='create_instance')

    command = _wrap_command(
        conf['gwas_id'],
        conf['url'],
        [
            "source /opt/conda/etc/profile.d/conda.sh",
            "conda activate ldsc",
            "cd ~/work",
            "python ~/gwas_processing/ldsc.py --bcf ./${ID}.vcf.gz --out ldsc.txt --ldsc_repo ~/gwas_processing/ldsc --ldsc_ref ~/ref/eur_w_ld_chr/",
            "conda deactivate",
            "curl -X PUT --data-binary '@ldsc.txt' ${URL}${ID}/ldsc.txt",
        ]
    )

    command_ocid = _oci_send_command_to_instance(agent_client, timeout, instance_ocid, command, conf['gwas_id'], 'ldsc')
    return command_ocid


def _task_report(agent_client, timeout, **context):
    conf = context['dag_run'].conf
    instance_ocid = context['task_instance'].xcom_pull(key='return_value', task_ids='create_instance')

    command = _wrap_command(
        conf['gwas_id'],
        conf['url'],
        [
            "source /opt/conda/etc/profile.d/conda.sh",
            "conda activate ieu-gwas-report",
            "cd ~/opengwas-reports",
            "Rscript render_gwas_report.R --n_cores 1 --refdata ~/ref/1kg/1kg_v3_nomult.bcf --output_dir ~/work/ ../work/${ID}.vcf.gz",
            "conda deactivate",
            "cd ~/work",
            "curl -X PUT --data-binary '@metadata.json' ${URL}${ID}/metadata.json",
            "curl -X PUT --data-binary '@qc_metrics.json' ${URL}${ID}/qc_metrics.json",
            "curl -X PUT --data-binary '@${ID}_report.html' ${URL}${ID}/${ID}_report.html",
        ]
    )

    command_ocid = _oci_send_command_to_instance(agent_client, timeout, instance_ocid, command, conf['gwas_id'], 'report')
    return command_ocid


def _task_delete_instance(instance_client, **context):
    instance_ocid = context['task_instance'].xcom_pull(key='return_value', task_ids='create_instance')

    status = _oci_terminate_instance(instance_client, instance_ocid)

    if status != 204:
        raise AirflowException("Unable to terminate the instance")

    return True


@dag(
    schedule=None,
    tags=['gwas']
)
def qc():
    compute_instances_client = _oci_init_compute_instance_client()
    compute_instance_agent_client = _oci_init_compute_instance_agent_client()

    timeouts = {
        'test_files': 30,
        'command_poll': 300,
        'create_instance': 300,
        'download_files': 300,
        'gwas2vcf': 86400,
        'clump': 3600,
        'ldsc': 3600,
        'report': 3600
    }

    test_files_on_oci = PythonSensor(
        task_id='test_files_on_oci',
        soft_fail=False,
        poke_interval=10,
        timeout=timeouts['test_files'],
        python_callable=_test_files_on_oci_object_storage,
        op_args=[['upload.txt.gz', '{GWAS_ID}.json']]
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
        poke_interval=15,
        timeout=timeouts['command_poll'] + timeouts['create_instance'] + timeouts['download_files'],
        python_callable=_test_command_execution,
        op_args=[compute_instance_agent_client, 'download']
    )

    gwas2vcf = PythonOperator(
        task_id='gwas2vcf',
        python_callable=_task_gwas2vcf,
        op_args=[compute_instance_agent_client, timeouts['gwas2vcf']]
    )

    test_vcf_files = PythonSensor(
        task_id='test_vcf_files',
        soft_fail=False,
        poke_interval=60,
        timeout=timeouts['command_poll'] + timeouts['gwas2vcf'],
        mode='reschedule',
        python_callable=_test_files_on_oci_object_storage,
        op_args=[['{GWAS_ID}.vcf.gz', '{GWAS_ID}.vcf.gz.tbi']]
    )

    clump = PythonOperator(
        task_id='clump',
        python_callable=_task_clump,
        op_args=[compute_instance_agent_client, timeouts['clump']]
    )

    test_clump_file = PythonSensor(
        task_id='test_clump_file',
        soft_fail=False,
        poke_interval=60,
        timeout=timeouts['command_poll'] + timeouts['clump'],
        mode='reschedule',
        python_callable=_test_files_on_oci_object_storage,
        op_args=[['clump.txt']]
    )

    ldsc = PythonOperator(
        task_id='ldsc',
        python_callable=_task_ldsc,
        op_args=[compute_instance_agent_client, timeouts['ldsc']]
    )

    test_ldsc_file = PythonSensor(
        task_id='test_ldsc_file',
        soft_fail=False,
        poke_interval=60,
        timeout=timeouts['command_poll'] + timeouts['ldsc'],
        mode='reschedule',
        python_callable=_test_files_on_oci_object_storage,
        op_args=[['ldsc.txt']]
    )

    report = PythonOperator(
        task_id='report',
        python_callable=_task_report,
        op_args=[compute_instance_agent_client, timeouts['report']]
    )

    test_report_files = PythonSensor(
        task_id='test_report_files',
        soft_fail=False,
        poke_interval=60,
        timeout=timeouts['command_poll'] + timeouts['report'],
        mode='reschedule',
        python_callable=_test_files_on_oci_object_storage,
        op_args=[['metadata.json', 'qc_metrics.json', '{GWAS_ID}_report.html']]
    )

    delete_instance = PythonOperator(
        task_id='delete_instance',
        python_callable=_task_delete_instance,
        op_args=[compute_instances_client]
    )

    test_files_on_oci >> create_instance >> download >> test_input_files >> gwas2vcf >> test_vcf_files >> clump >> test_clump_file >> ldsc >> test_ldsc_file >> report >> test_report_files >> delete_instance


qc()
