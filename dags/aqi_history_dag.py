from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta
from airflow.utils.dates import days_ago

# ─── Configuration ────────────────────────────────
default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    'start_date': days_ago(1),
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

# Dates de l’historique à récupérer (modifier au besoin)
START_DATE = "2025-06-01"
END_DATE = "2025-06-02"

# Fichier de sortie CSV
CSV_PATH = "/opt/airflow/data/aqi_10.csv"

# ─── DAG Definition ───────────────────────────────
with DAG(
    dag_id="aqi_history_dag",
    default_args=default_args,
    description="DAG pour télécharger, charger, et transformer les données AQI",
    schedule_interval="@once",  # à adapter si besoin
    catchup=False,
    tags=["aqi", "openmeteo", "postgres"],
) as dag:

    
    
    # 1. Télécharger l’historique AQI et générer aqi_all.csv
    table_raw = BashOperator(
        task_id="creation_table_raw",
        bash_command=(
            f"python3 /opt/airflow/scripts/etl/create_table_raw.py "
        )
    )
    
    
    # 1. Télécharger l’historique AQI et générer aqi_all.csv
    table_transform = BashOperator(
        task_id="creation_table_transform",
        bash_command=(
            f"python3 /opt/airflow/scripts/etl/create_table_transform.py "
        )
    )
    
    
    # 1. Télécharger l’historique AQI et générer aqi_all.csv
    fetch_csv = BashOperator(
        task_id="fetch_aqi_history_to_csv",
        bash_command=(
            f"python3 /opt/airflow/scripts/etl/history_aqi_to_csv.py "
            f"--start {START_DATE} --end {END_DATE} --out {CSV_PATH}"
        )
    )

    # 2. Charger dans la table brute aqi_raw
    load_to_raw = BashOperator(
        task_id="load_csv_to_table_raw",
        bash_command=(
            f"python3 /opt/airflow/scripts/etl/load_aqi_csv_to_table_raw.py "
            f"--csv {CSV_PATH}"
        )
    )

    # 3. Charger dans la table transformée aqi_transform
    load_to_transform = BashOperator(
        task_id="load_csv_to_table_transform",
        bash_command=(
            f"python3 /opt/airflow/scripts/etl/load_aqi_csv_to_table_transform.py "
            f"--csv {CSV_PATH}"
        )
    )

    # Dépendances
    [ table_raw, table_transform ] >> fetch_csv >> load_to_raw >> load_to_transform
