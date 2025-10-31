from datetime import datetime, timedelta

from airflow.sdk import dag, task
from airflow.models import Variable
from airflow.providers.http.operators.http import HttpOperator


@dag(
    tags=['gwas'],
    schedule='30 12 * * *',
    start_date=datetime(2025, 10, 12, 21, 0),
    catchup=False
)
def cache_gwas():
    timeouts = {
        'cache_gwasinfo': 300,
        'collect_associations_pos_indices': 600
    }

    cache_gwasinfo = HttpOperator(
        task_id='cache_gwasinfo',
        http_conn_id='api',
        endpoint='/api/maintenance/gwasinfo/cache',
        method='GET',
        headers={
            'X-SERVICE-KEY': Variable.get("SECRET_API_SERVICE_KEY")
        },
        extra_options={
            'timeout': timeouts['cache_gwasinfo']
        },
        retries=12,
        retry_delay=timedelta(seconds=300),
        log_response=True
    )

    collect_associations_pos_indices = HttpOperator(
        task_id='collect_associations_pos_indices',
        http_conn_id='api',
        endpoint='/api/maintenance/associations/collect_indices',
        method='GET',
        headers={
            'X-SERVICE-KEY': Variable.get("SECRET_API_SERVICE_KEY")
        },
        extra_options={
            'timeout': timeouts['collect_associations_pos_indices']
        },
        retries=12,
        retry_delay=timedelta(seconds=300),
        log_response=True
    )

    cache_gwasinfo, collect_associations_pos_indices

cache_gwas()
