from datetime import datetime

import requests
import logging

from airflow.decorators import dag, task
from airflow.models import Variable
from airflow.operators.http_operator import SimpleHttpOperator


# logging.getLogger('oci').setLevel(logging.DEBUG)
# logging.basicConfig()

@dag(tags=['gwas'], schedule_interval='*/2 * * * *', start_date=datetime(2024, 8, 22, 8, 40))
def callback():
    timeouts = {
        'refresh_added_by_status': 60
    }

    refresh_added_by_status = SimpleHttpOperator(
        task_id='refresh_added_by_status',
        http_conn_id='api',
        endpoint='/api/maintenance/refresh_added_by_status',
        method='GET',
        headers={
            'X-SERVICE-KEY': Variable.get("SECRET_API_SERVICE_KEY")
        },
        extra_options={
            'timeout': timeouts['refresh_added_by_status']
        },
        log_response=True
    )

    refresh_added_by_status

callback()
