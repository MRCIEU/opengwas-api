import oci
from hashlib import sha256

from airflow.models import Variable


def init_config() -> dict:
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


def init_compute_instance_client() -> oci.core.ComputeClient:
    return oci.core.ComputeClient(init_config())


def init_compute_instance_agent_client() -> oci.compute_instance_agent.ComputeInstanceAgentClient:
    return oci.compute_instance_agent.ComputeInstanceAgentClient(init_config())


def launch_instance(instance_client, display_name) -> str:
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
                boot_volume_size_in_gbs=65,
                image_id=Variable.get('OCI_IMAGE_ID')),
        ),
    )

    print(launch_instance_response.data)
    return launch_instance_response.data.id


def list_instance(instance_client, display_name):
    list_instances_response = instance_client.list_instances(
        compartment_id=Variable.get('OCI_COMPARTMENT_ID'),
        display_name=display_name,
        limit=50,
        sort_by="TIMECREATED",
        sort_order="ASC")

    print(list_instances_response.data)
    return list_instances_response.data


def send_command_to_instance(agent_client, timeout, instance_ocid, command, gwas_id, display_name):
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


def get_command_execution_result(agent_client, instance_ocid, command_ocid):
    get_instance_agent_command_execution_response = agent_client.get_instance_agent_command_execution(
        instance_agent_command_id=command_ocid,
        instance_id=instance_ocid)

    print(get_instance_agent_command_execution_response.data)
    return get_instance_agent_command_execution_response.data


def terminate_instance(instance_client, instance_ocid):
    terminate_instance_response = instance_client.terminate_instance(
        instance_id=instance_ocid,
        preserve_boot_volume=False,
        preserve_data_volumes_created_at_launch=False)

    print(terminate_instance_response.headers)
    return terminate_instance_response.status
