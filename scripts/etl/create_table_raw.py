"""
create_aqi_table.py
~~~~~~~~~~~~~~~~~~~
Exécute ce script une seule fois pour créer la table `aqi_current` dans
ta base Postgres.

Variables d’environnement reconnues :
  POSTGRES_HOST  (def. localhost)
  POSTGRES_DB    (def. aqi)
  POSTGRES_USER  (def. postgres)
  POSTGRES_PASSWORD (def. postgres)
  POSTGRES_PORT  (def. 5432)
"""

import os
import psycopg2

PG_CONN_INFO = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "database": os.getenv("POSTGRES_DB", "aqi"),
    "user": os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
    "port": int(os.getenv("POSTGRES_PORT", 5432)),
}

CREATE_TABLE_RAW_SQL = """
CREATE TABLE IF NOT EXISTS aqi_raw (
    id SERIAL PRIMARY KEY,
    city TEXT NOT NULL,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    time TIMESTAMPTZ NOT NULL,
    interval INTEGER,
    european_aqi INTEGER,
    pm10 NUMERIC,
    pm2_5 NUMERIC,
    carbon_monoxide NUMERIC,
    nitrogen_dioxide NUMERIC,
    sulphur_dioxide NUMERIC,
    ozone NUMERIC,
    aerosol_optical_depth NUMERIC,
    dust NUMERIC,
    uv_index NUMERIC,
    uv_index_clear_sky NUMERIC,
    ammonia NUMERIC,
    alder_pollen NUMERIC,
    birch_pollen NUMERIC,
    grass_pollen NUMERIC,
    mugwort_pollen NUMERIC,
    olive_pollen NUMERIC,
    ragweed_pollen NUMERIC
    --UNIQUE (city, time)  -- évite un doublon pour la même ville et la même heure
);
"""

def create_table() -> None:
    with psycopg2.connect(**PG_CONN_INFO) as conn:
        with conn.cursor() as cur:
            cur.execute(CREATE_TABLE_RAW_SQL)
    print("✓ Table aqi_current créée (ou déjà existante)")

if __name__ == "__main__":
    create_table()
