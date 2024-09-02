from datetime import datetime

from airflow.decorators import dag, task
from airflow.models import Variable
from airflow.operators.http_operator import SimpleHttpOperator


@dag(tags=['gwas'], schedule_interval='*/5 * * * *', start_date=datetime(2024, 8, 31, 20, 45))
def cache_stats():
    timeouts = {
        'cache_stats_mvd': 300,
        'cache_stats_mau': 300
    }

    cache_stats_mvd = SimpleHttpOperator(
        task_id='cache_stats_mvd',
        http_conn_id='api',
        endpoint='/api/maintenance/stats/mvd/cache',
        method='GET',
        headers={
            'X-SERVICE-KEY': Variable.get("SECRET_API_SERVICE_KEY")
        },
        data={
            'year': datetime.today().strftime("%Y"),
            'month': datetime.today().strftime("%m")
        },
        extra_options={
            'timeout': timeouts['cache_stats_mvd']
        },
        log_response=True
    )

    cache_stats_mau = SimpleHttpOperator(
        task_id='cache_stats_mau',
        http_conn_id='api',
        endpoint='/api/maintenance/stats/mau/cache',
        method='GET',
        headers={
            'X-SERVICE-KEY': Variable.get("SECRET_API_SERVICE_KEY")
        },
        data={
            'year': datetime.today().strftime("%Y"),
            'month': datetime.today().strftime("%m")
        },
        extra_options={
            'timeout': timeouts['cache_stats_mau']
        },
        log_response=True
    )

    cache_stats_mvd >> cache_stats_mau

cache_stats()
