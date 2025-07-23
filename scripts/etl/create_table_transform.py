# ------------------------------------------------------------
# Crée la table `aqi_transform` destinée à recevoir les messages
# « transformés » (sous-ensemble de variables AQI + métadonnées).
#
# Variables d’environnement reconnues
# -----------------------------------
# POSTGRES_HOST
# POSTGRES_DB
# POSTGRES_USER
# POSTGRES_PASSWORD
# POSTGRES_PORT
#
# Exécution :
#   python create_aqi_transform_table.py
# ------------------------------------------------------------

import os
import psycopg2

PG_CONN_INFO = {
    "host":     os.getenv("POSTGRES_HOST", "localhost"),
    "database": os.getenv("POSTGRES_DB",   "aqi"),
    "user":     os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
    "port":     int(os.getenv("POSTGRES_PORT", 5432)),
}

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS aqi_transform (
    id SERIAL PRIMARY KEY,
    time TIMESTAMPTZ NOT NULL,
    city TEXT          NOT NULL,
    latitude  DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    european_aqi      NUMERIC,
    pm2_5             NUMERIC,
    pm10              NUMERIC,
    carbon_monoxide   NUMERIC,
    sulphur_dioxide   NUMERIC,
    uv_index          NUMERIC
    --UNIQUE (city, time)               -- évite les doublons d'horodatage
);
"""

def create_table() -> None:
    with psycopg2.connect(**PG_CONN_INFO) as conn:
        with conn.cursor() as cur:
            cur.execute(CREATE_TABLE_SQL)
    print("✓ Table aqi_transform créée ou déjà existante")

if __name__ == "__main__":
    create_table()
