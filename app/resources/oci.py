import oci

from resources.globals import Globals


class OCI:
    def __init__(self):
        config = {
            "user": Globals.app_config['oci']['auth']['user'],
            "fingerprint": Globals.app_config['oci']['auth']['fingerprint'],
            "tenancy": Globals.app_config['oci']['auth']['tenancy'],
            "region": Globals.app_config['oci']['auth']['region'],
            "key_file": Globals.app_config['oci']['auth']['key_file']
        }
        oci.config.validate_config(config)
        self.object_storage_client = oci.object_storage.ObjectStorageClient(config)

    def object_storage_list(self, bucket_key, prefix):
        r = self.object_storage_client.list_objects(
            namespace_name=Globals.app_config['oci']['object_storage']['namespace_name'],
            bucket_name=Globals.app_config['oci']['object_storage']['bucket_names'][bucket_key],
            prefix=prefix
        )
        return [o.name for o in r.data.objects]

    def object_storage_upload(self, bucket_key, object_name, object_body):
        return self.object_storage_client.put_object(
            namespace_name=Globals.app_config['oci']['object_storage']['namespace_name'],
            bucket_name=Globals.app_config['oci']['object_storage']['bucket_names'][bucket_key],
            object_name=object_name,
            put_object_body=object_body,
        )

    def object_storage_delete(self, bucket_key, object_name):
        return self.object_storage_client.delete_object(
            namespace_name=Globals.app_config['oci']['object_storage']['namespace_name'],
            bucket_name=Globals.app_config['oci']['object_storage']['bucket_names'][bucket_key],
            object_name=object_name
        )

    def object_storage_delete_by_prefix(self, bucket_key, prefix):
        object_names = self.object_storage_list(bucket_key, prefix)
        for o in object_names:
            self.object_storage_delete(bucket_key, o)
        return object_names

    def object_storage_download(self, bucket_key, object_name):
        return self.object_storage_client.get_object(
            namespace_name=Globals.app_config['oci']['object_storage']['namespace_name'],
            bucket_name=Globals.app_config['oci']['object_storage']['bucket_names'][bucket_key],
            object_name=object_name
        )
