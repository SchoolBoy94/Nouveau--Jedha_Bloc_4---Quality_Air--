import os
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

# Connexion Postgres
PG_CONN_INFO = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "database": os.getenv("POSTGRES_DB", "aqi"),
    "user": os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
    "port": int(os.getenv("POSTGRES_PORT", 5432)),
}

# Colonnes à conserver pour aqi_transform
TRANSFORM_COLUMNS = [
    "time", "city", "latitude", "longitude",
    "european_aqi", "pm2_5", "pm10",
    "carbon_monoxide", "sulphur_dioxide", "uv_index"
]

def load_transform_csv(csv_path: str) -> None:
    print(f"📂 Lecture de {csv_path}...")
    df = pd.read_csv(csv_path)

    if df.empty:
        print("⚠️  Le fichier CSV est vide.")
        return

    # Conversion du timestamp
    df["time"] = pd.to_datetime(df["time"], utc=True)

    # Filtrage des colonnes nécessaires
    df = df[TRANSFORM_COLUMNS]

    # Remplace les NaN par None pour l'insertion
    rows = df.where(pd.notnull(df), None).values.tolist()

    insert_sql = f"""
        INSERT INTO aqi_transform ({", ".join(TRANSFORM_COLUMNS)})
        VALUES %s
    """

    print(f"🔄 Insertion de {len(rows)} lignes dans aqi_transform...")
    with psycopg2.connect(**PG_CONN_INFO) as conn:
        with conn.cursor() as cur:
            execute_values(cur, insert_sql, rows)

    print("✅ Insertion terminée avec succès.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Charge le CSV AQI dans la table transformée.")
    parser.add_argument("--csv", required=True, help="Chemin du fichier CSV (aqi_all.csv)")
    args = parser.parse_args()

    load_transform_csv(args.csv)
