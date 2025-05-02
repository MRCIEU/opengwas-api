from datetime import datetime, timedelta

from airflow.decorators import dag
from airflow.operators.bash_operator import BashOperator


@dag(
    tags=['airflow'],
    schedule_interval='* 0 * * *',
    start_date=datetime.now(),
    catchup=False
)
def airflow_cleanup():
    days_to_keep = 90

    cleanup_logs = BashOperator(
        task_id='cleanup_logs',
        bash_command=f"""
        BASE_FOLDER="/opt/airflow/logs"
        echo "Cleaning up logs"
        find $BASE_FOLDER ! -path '*/dag_id=qc/*' ! -path '*/dag_id=release/*' -type f -name "*.log" -mtime +{days_to_keep} -print -delete
        find $BASE_FOLDER/dag_processor_manager -type f -name "*.log.*" -mtime +{days_to_keep} -print -delete
        find $BASE_FOLDER ! -path '*/dag_id=qc/*' ! -path '*/dag_id=release/*' -type d -empty -delete
        """
    )

    cleanup_dag_runs = BashOperator(
        task_id='cleanup_dag_runs',
        bash_command=f"""
            airflow db clean --clean-before-timestamp {(datetime.today() - timedelta(days_to_keep)).strftime("%Y-%m-%d")} -v -y
            """
    )

    cleanup_logs >> cleanup_dag_runs

airflow_cleanup()
