from datetime import datetime

from airflow.decorators import dag, task
from airflow.models import Variable
from airflow.operators.http_operator import SimpleHttpOperator


@dag(tags=['gwas'], schedule_interval='0 1 * * *', start_date=datetime(2024, 12, 13, 1, 0))
def cache_gwasinfo():
    timeouts = {
        'cache_gwasinfo': 300
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
        log_response=True
    )

    cache_gwasinfo

cache_gwasinfo()
