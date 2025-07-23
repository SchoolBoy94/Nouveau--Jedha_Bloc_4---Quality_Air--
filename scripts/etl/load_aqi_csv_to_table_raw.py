import os
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime

# Connexion Postgres
PG_CONN_INFO = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "database": os.getenv("POSTGRES_DB", "aqi"),
    "user": os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
    "port": int(os.getenv("POSTGRES_PORT", 5432)),
}

# Liste des colonnes de la table (dans l'ordre)
DB_COLUMNS = [
    "city", "latitude", "longitude", "time", "interval", "european_aqi",
    "pm10", "pm2_5", "carbon_monoxide", "nitrogen_dioxide",
    "sulphur_dioxide", "ozone", "aerosol_optical_depth", "dust",
    "uv_index", "uv_index_clear_sky", "ammonia",
    "alder_pollen", "birch_pollen", "grass_pollen", "mugwort_pollen",
    "olive_pollen", "ragweed_pollen"
]

def load_csv_to_postgres(csv_path: str) -> None:
    print(f"📂 Lecture de {csv_path}...")
    df = pd.read_csv(csv_path)

    if df.empty:
        print("⚠️  Le fichier CSV est vide.")
        return

    # Ajoute une colonne 'interval' manquante si nécessaire
    if 'interval' not in df.columns:
        df["interval"] = None  # ou une valeur par défaut comme 3600

    # Reconvertit la colonne 'time' si besoin
    df["time"] = pd.to_datetime(df["time"], utc=True)

    # Garde uniquement les colonnes attendues dans le bon ordre
    df = df[DB_COLUMNS]

    # Convertit les NaN en None (pour psycopg2)
    rows = df.where(pd.notnull(df), None).values.tolist()

    insert_sql = f"""
        INSERT INTO aqi_raw ({", ".join(DB_COLUMNS)})
        VALUES %s
    """

    print(f"🔄 Insertion de {len(rows)} lignes dans la base...")
    with psycopg2.connect(**PG_CONN_INFO) as conn:
        with conn.cursor() as cur:
            execute_values(cur, insert_sql, rows)

    print("✅ Insertion terminée avec succès.")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Charge un CSV AQI dans la base Postgres.")
    parser.add_argument("--csv", required=True, help="Chemin vers le fichier CSV")
    args = parser.parse_args()

    load_csv_to_postgres(args.csv)
