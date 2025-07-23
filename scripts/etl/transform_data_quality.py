# ------------------------------------------------------------------
# Contrôle qualité de la table Postgres `aqi_transform`
# + notification Discord en cas d’échec.
# ------------------------------------------------------------------

from __future__ import annotations
import os
from datetime import datetime, timezone
import pandas as pd
import requests
from sqlalchemy import create_engine

# ------------------------------------------------------------------
# Connexion Postgres  (modifie si besoin)
# ------------------------------------------------------------------
PG_CONN_STR = os.getenv(
    "PG_CONN_STR",
    "postgresql+psycopg2://postgres:postgres@postgres:5432/aqi",
)

# ------------------------------------------------------------------
# Webhook Discord  (mettre ton URL)
# ------------------------------------------------------------------
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1396617999711998073/oPIRNwsrq7pKon1etshSo7GdUU5jeiybW4_I53iGQesNw1gnRSJPsD3tE8no4zeHFMCH"
#  = os.getenv("DISCORD_WEBHOOK_URL", "")

def send_discord_notification(message: str) -> None:
    """Envoie un message texte au webhook Discord."""
    if not DISCORD_WEBHOOK_URL:
        print("⚠️  DISCORD_WEBHOOK_URL non défini — pas de notification.")
        return
    try:
        r = requests.post(DISCORD_WEBHOOK_URL, json={"content": message}, timeout=10)
        r.raise_for_status()
        print("✅ Notification Discord envoyée.")
    except Exception as exc:
        print(f"❌ Échec Discord : {exc}")

# ------------------------------------------------------------------
# Paramètres de validation
# ------------------------------------------------------------------
TABLE = "aqi_transform"

REQ_COLS = [
    "time", "city", "latitude", "longitude",
    "european_aqi", "pm2_5", "pm10",
    "carbon_monoxide", "sulphur_dioxide", "uv_index",
]

RANGES = {
    "european_aqi":    (0, 500),
    "pm2_5":           (0, 500),
    "pm10":            (0, 600),
    "carbon_monoxide": (0, 10000),
    "sulphur_dioxide": (0, 2000),
    "uv_index":        (0, 15),
}



def check_aqi_transform_quality_and_alert() -> None:
    engine = create_engine(PG_CONN_STR)
    df = pd.read_sql(f"SELECT * FROM {TABLE}", engine)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    errors: list[str] = []
    examples: list[str] = []

    if df.empty:
        errors.append(f"❗ La table `{TABLE}` est vide.")
    else:
        # Champs requis manquants
        missing_cols = [c for c in REQ_COLS if c not in df.columns]
        if missing_cols:
            errors.append(f"Colonnes manquantes : {', '.join(missing_cols)}")

        # Valeurs NULL
        for c in REQ_COLS:
            null_rows = df[df[c].isnull()]
            if not null_rows.empty:
                errors.append(f"- {len(null_rows)} valeurs NULL dans `{c}`")
                examples.append(f"Ex. NULL dans `{c}` :\n" + null_rows[["city", "time"]].head(3).to_string())

        # time dans le futur
        df["time"] = pd.to_datetime(df["time"], errors="coerce", utc=True)
        futur = df[df["time"] > pd.Timestamp.now(tz=timezone.utc)]
        if not futur.empty:
            errors.append(f"- {len(futur)} horodatages `time` dans le futur")
            examples.append("Ex. futurs :\n" + futur[["city", "time"]].head(3).to_string())

        # Latitude / Longitude
        bad_lat = df[(df["latitude"] < -90) | (df["latitude"] > 90)]
        if not bad_lat.empty:
            errors.append(f"- {len(bad_lat)} latitudes invalides")
            examples.append("Ex. lat invalides :\n" + bad_lat[["city", "latitude"]].head(3).to_string())

        bad_lon = df[(df["longitude"] < -180) | (df["longitude"] > 180)]
        if not bad_lon.empty:
            errors.append(f"- {len(bad_lon)} longitudes invalides")
            examples.append("Ex. lon invalides :\n" + bad_lon[["city", "longitude"]].head(3).to_string())

        # Polluants hors plage
        for col, (lo, hi) in RANGES.items():
            bad = df[(df[col] < lo) | (df[col] > hi) | df[col].isnull()]
            if not bad.empty:
                errors.append(f"- {len(bad)} valeurs hors plage pour `{col}`")
                examples.append(f"Ex. `{col}` hors plage :\n" + bad[["city", col]].head(3).to_string())

        # Doublons
        dup_rows = df[df.duplicated(subset=["city", "time"], keep=False)]
        if not dup_rows.empty:
            errors.append(f"- {len(dup_rows)} doublons sur (city, time)")
            examples.append("Ex. doublons :\n" + dup_rows[["city", "time"]].head(3).to_string())

    # Rapport final
    if errors:
        report = (
            f"📅 Contrôle qualité : {now}\n\n"
            f"❌ ÉCHEC sur `{TABLE}` ({len(df)} lignes)\n\n"
            + "\n\n".join(examples) + "\n\n"
            + "Erreurs détectées :\n" + "\n".join(errors)
        )
        print(report)
        send_discord_notification(report)
        print("⚠️  Contrôle échoué, mais tâche marquée comme succès.")
        return
    else:
        print(f"✅ Qualité OK : {len(df)} lignes — {now}")
# ------------------------------------------------------------------
if __name__ == "__main__":
    check_aqi_transform_quality_and_alert()
