import os
import requests


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
