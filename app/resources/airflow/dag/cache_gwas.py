from datetime import datetime, timedelta

from airflow.decorators import dag, task
from airflow.models import Variable
from airflow.operators.http_operator import SimpleHttpOperator


@dag(
    tags=['gwas'],
    schedule_interval='0 1 * * *',
    start_date=datetime(2025, 2, 6, 1, 0),
    catchup=False
)
def cache_gwas():
    timeouts = {
        'cache_gwasinfo': 300,
        'collect_associations_pos_indices': 600
    }

    cache_gwasinfo = SimpleHttpOperator(
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
        retries=10,
        retry_delay=timedelta(seconds=30),
        log_response=True
    )

    collect_associations_pos_indices = SimpleHttpOperator(
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
        retries=8,
        retry_delay=timedelta(seconds=30),
        log_response=True
    )

    cache_gwasinfo
    cache_gwasinfo, collect_associations_pos_indices

cache_gwas()
