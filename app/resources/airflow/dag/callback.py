from datetime import datetime, timedelta

from airflow.sdk import dag, task
from airflow.models import Variable
from airflow.providers.http.operators.http import HttpOperator


@dag(
    tags=['gwas'],
    schedule='*/5 * * * *',
    start_date=datetime(2025, 10, 12, 21, 0),
    catchup=False
)
def callback():
    timeouts = {
        'refresh_added_by_status': 60
    }

    refresh_added_by_status = HttpOperator(
        task_id='refresh_added_by_status',
        http_conn_id='api',
        endpoint='/api/maintenance/pipeline/added_by_state/refresh',
        method='GET',
        headers={
            'X-SERVICE-KEY': Variable.get("SECRET_API_SERVICE_KEY")
        },
        extra_options={
            'timeout': timeouts['refresh_added_by_status']
        },
        retries=6,
        retry_delay=timedelta(seconds=30),
        log_response=True
    )

    refresh_added_by_status

callback()
