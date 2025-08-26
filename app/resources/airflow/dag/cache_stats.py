from datetime import datetime, timedelta

from airflow.decorators import dag
from airflow.models import Variable
from airflow.operators.http_operator import SimpleHttpOperator


@dag(
    tags=['gwas'],
    schedule_interval='0 * * * *',
    start_date=datetime(2025, 5, 29, 21, 0),
    catchup=False
)
def cache_stats():
    timeouts = {
        'cache_stats_mvd': 300,
        'cache_stats_mau': 300,
        'cache_stats_recent_week': 300,
    }

    cache_stats_mvd = SimpleHttpOperator(
        task_id='cache_stats_mvd',
        http_conn_id='api',
        endpoint='/api/maintenance/stats/mvd/cache',
        method='GET',
        headers={
            'X-SERVICE-KEY': Variable.get("SECRET_API_SERVICE_KEY"),
        },
        data={
            'year': datetime.today().strftime("%Y"),
            'month': datetime.today().strftime("%m"),
        },
        extra_options={
            'timeout': timeouts['cache_stats_mvd'],
        },
        retries=20,
        retry_delay=timedelta(seconds=60),
        log_response=True
    )

    cache_stats_mau = SimpleHttpOperator(
        task_id='cache_stats_mau',
        http_conn_id='api',
        endpoint='/api/maintenance/stats/mau/cache',
        method='GET',
        headers={
            'X-SERVICE-KEY': Variable.get("SECRET_API_SERVICE_KEY"),
        },
        data={
            'year': datetime.today().strftime("%Y"),
            'month': datetime.today().strftime("%m"),
        },
        extra_options={
            'timeout': timeouts['cache_stats_mau'],
        },
        retries=20,
        retry_delay=timedelta(seconds=60),
        log_response=True
    )

    cache_stats_recent_week = SimpleHttpOperator(
        task_id='cache_stats_recent_week',
        http_conn_id='api',
        endpoint='/api/maintenance/stats/recent_week/cache',
        method='GET',
        headers={
            'X-SERVICE-KEY': Variable.get("SECRET_API_SERVICE_KEY"),
        },
        extra_options={
            'timeout': timeouts['cache_stats_recent_week']
        },
        retries=20,
        retry_delay=timedelta(seconds=60),
        log_response=True
    )

    cache_stats_mvd >> cache_stats_mau >> cache_stats_recent_week

cache_stats()
