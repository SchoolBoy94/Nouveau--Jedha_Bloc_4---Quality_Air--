# from airflow import DAG
# from airflow.operators.python import PythonOperator
# from datetime import datetime, timedelta
# import sys
# import os
# from airflow.utils.dates import days_ago

# # Ajouter le chemin du dossier contenant ton script
# sys.path.append("/opt/airflow/scripts")  # adapte ce chemin si besoin

# from transform_data_quality import check_aqi_transform_quality_and_alert

# default_args = {
#     "owner": "airflow",
#     "retries": 0,
#     'start_date': days_ago(1),
#     "retry_delay": timedelta(minutes=5),
# }

# with DAG(
#     dag_id="check_transform_quality_dag",
#     default_args=default_args,
#     schedule_interval="@daily",  # tu peux changer à chaque heure si tu veux: "0 * * * *"
#     catchup=False,
#     tags=["data_quality", "aqi"],
# ) as dag:

#     check_quality = PythonOperator(
#         task_id="check_aqi_transform_quality",
#         python_callable=check_aqi_transform_quality_and_alert,
#     )

#     check_quality




from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import timedelta
from airflow.utils.dates import days_ago
import sys
import os
import requests

# Ajouter le chemin du dossier contenant ton script
sys.path.append("/opt/airflow/scripts")  # adapte ce chemin si besoin

from etl.transform_data_quality import check_aqi_transform_quality_and_alert

# ──────────────────────────────────────────────
# Chargement du .env pour exécutions locales
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1396617999711998073/oPIRNwsrq7pKon1etshSo7GdUU5jeiybW4_I53iGQesNw1gnRSJPsD3tE8no4zeHFMCH"
#  = os.getenv("DISCORD_WEBHOOK_URL")

def send_discord_notification(context):
    """
    Envoie une notification Discord quand une tâche Airflow échoue.
    """
    dag_id = context.get('dag').dag_id
    task_id = context.get('task_instance').task_id
    execution_date = context.get('execution_date')
    log_url = context.get('task_instance').log_url

    content = (
        f"🚨 **ALERTE DAG Airflow** 🚨\n"
        f"DAG: `{dag_id}`\n"
        f"Tâche: `{task_id}` a échoué\n"
        f"Date d'exécution: {execution_date}\n"
        f"[Voir les logs]({log_url})"
    )

    data = {"content": content}
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=data)
        if response.status_code != 204:
            print(f"Erreur Discord: {response.status_code} {response.text}")
    except Exception as e:
        print(f"Exception lors de l'envoi Discord: {e}")

# ──────────────────────────────────────────────
default_args = {
    "owner": "airflow",
    "retries": 0,
    'start_date': days_ago(1),
    "retry_delay": timedelta(minutes=5),
    "on_failure_callback": send_discord_notification,  # callback en cas d’échec
}

with DAG(
    dag_id="check_transform_quality_dag",
    default_args=default_args,
    schedule_interval="@daily",
    catchup=False,
    tags=["data_quality", "aqi"],
) as dag:

    check_quality = PythonOperator(
        task_id="check_aqi_transform_quality",
        python_callable=check_aqi_transform_quality_and_alert,
    )

    check_quality
