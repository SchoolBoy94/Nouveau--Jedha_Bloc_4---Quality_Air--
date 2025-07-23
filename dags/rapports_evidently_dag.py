# /opt/airflow/dags/rapports_evidently.py

from datetime import datetime
from airflow.decorators import dag
from airflow.operators.bash import BashOperator

@dag(
    schedule_interval="@daily",
    start_date=datetime(2025, 7, 1),
    catchup=False,
    tags=["aqi", "evidently"]
)
def build_evidently_reports():
    run_report = BashOperator(
        task_id="run_evidently",
        bash_command="python /opt/airflow/scripts/etl/run_evidently.py",
        env={"PYTHONPATH": "/opt/airflow"}
    )

    run_report

build_evidently_reports = build_evidently_reports()
