from datetime import datetime, timedelta

import oci

from resources.globals import Globals


def get_oci_config():
        config = {
            "user": Globals.app_config['oci']['auth']['user'],
            "fingerprint": Globals.app_config['oci']['auth']['fingerprint'],
            "tenancy": Globals.app_config['oci']['auth']['tenancy'],
            "region": Globals.app_config['oci']['auth']['region'],
            "key_file": Globals.app_config['oci']['auth']['key_file']
        }
        oci.config.validate_config(config)
        return config


class OCIObjectStorage:
    def __init__(self):
        self.object_storage_client = oci.object_storage.ObjectStorageClient(get_oci_config())
        self.object_storage_client.base_client.session.adapters['http://'].poolmanager.connection_pool_kw['maxsize'] = 100
        self.object_storage_client.base_client.session.adapters['https://'].poolmanager.connection_pool_kw['maxsize'] = 100

    def object_storage_list(self, bucket_key, prefix):
        results = []
        start = ''

        while True:
            r = self.object_storage_client.list_objects(
                namespace_name=Globals.app_config['oci']['object_storage']['namespace_name'],
                bucket_name=Globals.app_config['oci']['object_storage']['bucket_names'][bucket_key],
                prefix=prefix,
                start=start
            )
            results.extend([o.name for o in r.data.objects])
            if not r.data.next_start_with:
                break
            start = r.data.next_start_with

        return results

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

    def object_storage_par_create(self, bucket_key, object_name, access_type, listing_action: str, expire_in_seconds: int, url_name):
        """
        Create Pre-Authenticated Request (PAR) of object storage
            https://docs.oracle.com/en-us/iaas/api/#/en/objectstorage/20160918/PreauthenticatedRequest/
            For any object under a directory, set object_name to <dir_name>/ and access_type to AnyObject{Read|Write|ReadWrite}
        :param bucket_key:
        :param object_name:
        :param access_type: ObjectRead | ObjectWrite | ObjectReadWrite | AnyObjectWrite | AnyObjectRead | AnyObjectReadWrite
        :param listing_action: Deny | ListObjects
        :param expire_in_seconds:
        :param url_name: Self-explanatory name for this PAR
        :return:
        """
        return self.object_storage_client.create_preauthenticated_request(
            namespace_name=Globals.app_config['oci']['object_storage']['namespace_name'],
            bucket_name=Globals.app_config['oci']['object_storage']['bucket_names'][bucket_key],
            create_preauthenticated_request_details=oci.object_storage.models.CreatePreauthenticatedRequestDetails(
                name=url_name,
                access_type=access_type,
                time_expires=datetime.now() + timedelta(0, expire_in_seconds),
                bucket_listing_action=listing_action,
                object_name=object_name)
        ).data.full_path

    # Note: this is async
    def object_storage_copy(self, src_bucket_key, src_object_name, dst_bucket_key, dst_object_name):
        return self.object_storage_client.copy_object(
            namespace_name=Globals.app_config['oci']['object_storage']['namespace_name'],
            bucket_name=Globals.app_config['oci']['object_storage']['bucket_names'][src_bucket_key],
            copy_object_details=oci.object_storage.models.CopyObjectDetails(
                source_object_name=src_object_name,
                destination_region=Globals.app_config['oci']['object_storage']['region'],
                destination_namespace=Globals.app_config['oci']['object_storage']['namespace_name'],
                destination_bucket=Globals.app_config['oci']['object_storage']['bucket_names'][dst_bucket_key],
                destination_object_name=dst_object_name),
        )

    # Note: this is async
    def object_storage_copy_by_prefix(self, src_bucket_key, prefix, dst_bucket_key, dst_object_name):
        object_names = self.object_storage_list(src_bucket_key, prefix)
        for o in object_names:
            self.object_storage_copy(src_bucket_key, o, dst_bucket_key, dst_object_name)
        return object_names


# class OCIEmailDP:
#     def __init__(self):
#         self.email_dp_client = oci.email_data_plane.EmailDPClient(get_oci_config())
#
#     def send_email(self, recipients, subject, body_html):
#         return self.email_dp_client.submit_email(oci.email_data_plane.models.SubmitEmailDetails(
#             body_html=body_html,
#             recipients=oci.email_data_plane.models.Recipients(
#                 to=[oci.email_data_plane.models.EmailAddress(
#                     email=r
#                 ) for r in recipients],
#             ),
#             sender=oci.email_data_plane.models.Sender(
#                 compartment_id=Globals.app_config['oci']['email_delivery']['compartment_id'],
#                 sender_address=oci.email_data_plane.models.EmailAddress(
#                     email=Globals.app_config['oci']['email_delivery']['sender']['email'],
#                     name=Globals.app_config['oci']['email_delivery']['sender']['name']
#                 )
#             ),
#             subject=subject
#         ))
