from __future__ import annotations
import json, os, sys, logging
from typing import List, Optional

import pandas as pd
import psycopg2
from psycopg2.extras import execute_batch
from kafka import KafkaConsumer

# ─── Logger lisible dans Airflow / console ────────────────────────────────
log = logging.getLogger("insert_table_raw")
log.setLevel(logging.INFO)
log.addHandler(logging.StreamHandler(sys.stdout))

# ─── Connexion PostgreSQL --------------------------------------------------
def _pg_conn():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        database=os.getenv("POSTGRES_DB", "aqi"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
    )

def df_to_postgres_batch(df: pd.DataFrame, table: str):
    with _pg_conn() as conn, conn.cursor() as cur:
        cols = list(df.columns)
        sql  = (
            f"INSERT INTO {table} ({', '.join(cols)}) "
            f"VALUES ({', '.join(['%s'] * len(cols))}) "
            "ON CONFLICT DO NOTHING"
        )
        execute_batch(cur, sql, df.values.tolist())
    log.info("✅ INSERT %s → %s", len(df), table)

# ─── Kafka & tables --------------------------------------------------------
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
TOPIC_RAW    = os.getenv("TOPIC_AQI_RAW", "aqi_current")
TABLE_RAW    = os.getenv("TABLE_AQI_RAW", "aqi_raw")

EXPECTED_COLS: List[str] = [
    "run_id", "time", "city", "latitude", "longitude", "interval",
    "european_aqi", "pm10", "pm2_5", "carbon_monoxide", "nitrogen_dioxide",
    "sulphur_dioxide", "ozone", "ammonia", "uv_index_clear_sky", "uv_index",
    "dust", "aerosol_optical_depth", "ragweed_pollen", "olive_pollen",
    "mugwort_pollen", "grass_pollen", "birch_pollen", "alder_pollen",
]

# ─── Consumer principal ----------------------------------------------------
def consume_kafka_to_table(run_id: str, max_records: Optional[int] = None) -> int:
    consumer = KafkaConsumer(
        TOPIC_RAW,
        bootstrap_servers=KAFKA_BROKER,
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        group_id=f"aqi_raw_loader_{run_id}",          # 1 groupe ≈ 1 run
        consumer_timeout_ms=10_000,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
    )

    records = [
        msg.value
        for idx, msg in enumerate(consumer, 1)
        if msg.value.get("run_id") == run_id and (max_records is None or idx <= max_records)
    ]

    consumer.commit(); consumer.close()

    if not records:
        log.warning("⚠️  Aucun message pour run_id=%s — rien inséré.", run_id)
        return 0

    df = pd.DataFrame(records).reindex(columns=EXPECTED_COLS, fill_value=None)
    df.drop(columns=["run_id"], inplace=True)        # on ne stocke pas la clé technique
    try:
        df_to_postgres_batch(df, TABLE_RAW)
    except Exception as err:
        log.error("❌ INSERT échoué : %s", err, exc_info=True)
        raise

    return len(df)

# ---------------------------------------------------------------------------
if __name__ == "__main__":
    consume_kafka_to_table(run_id="debug")
