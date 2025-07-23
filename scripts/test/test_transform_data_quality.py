import os
from etl.transform_data_quality import check_aqi_transform_quality_and_alert

# Optionnel : si ta connexion à Postgres est via une autre chaîne
os.environ["PG_CONN_STR"] = "postgresql+psycopg2://postgres:postgres@localhost:5432/aqi"

# Optionnel : si tu veux recevoir les messages sur Discord
os.environ["DISCORD_WEBHOOK_URL"] = "https://discord.com/api/webhooks/..."  # ton vrai webhook

# Lancement du test qualité
try:
    check_aqi_transform_quality_and_alert()
except ValueError as e:
    print("🚨 Test terminé avec erreurs détectées.")
except Exception as e:
    print("❌ Erreur inattendue :", str(e))
else:
    print("✅ Test terminé sans anomalies.")
