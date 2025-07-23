from __future__ import annotations
import json, os
from typing import List, Optional, Tuple
from datetime import datetime
import psycopg2
from kafka import KafkaConsumer
from psycopg2.extras import execute_batch

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
TOPIC_TRANS  = os.getenv("TOPIC_AQI_TRANSFORMED", "aqi_transformed")
TABLE_TRANS  = os.getenv("TABLE_AQI_TRANSFORM", "aqi_transform")

PG_CONN = {
    "host": os.getenv("POSTGRES_HOST","localhost"),
    "database": os.getenv("POSTGRES_DB","aqi"),
    "user": os.getenv("POSTGRES_USER","postgres"),
    "password": os.getenv("POSTGRES_PASSWORD","postgres"),
    "port": int(os.getenv("POSTGRES_PORT",5432)),
}

COLS = ["time","city","latitude","longitude",
        "european_aqi","pm2_5","pm10",
        "carbon_monoxide","sulphur_dioxide","uv_index"]

SQL = f"INSERT INTO {TABLE_TRANS} ({', '.join(COLS)}) " \
      f"VALUES ({', '.join(['%s']*len(COLS))}) ON CONFLICT DO NOTHING"

def _tuple(msg: dict) -> Tuple:
    return (datetime.fromisoformat(msg["time"]),
            msg.get("city"), msg.get("latitude"), msg.get("longitude"),
            msg.get("european_aqi"), msg.get("pm2_5"), msg.get("pm10"),
            msg.get("carbon_monoxide"), msg.get("sulphur_dioxide"),
            msg.get("uv_index"),)

def insert_from_kafka(run_id: str, max_records: Optional[int]=None) -> int:
    cons = KafkaConsumer(
        TOPIC_TRANS, bootstrap_servers=KAFKA_BROKER,
        auto_offset_reset="earliest", enable_auto_commit=False,
        group_id="aqi_transform_loader", consumer_timeout_ms=10000,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
    )
    rows=[]
    for i,msg in enumerate(cons,1):
        if msg.value.get("run_id")==run_id:
            rows.append(_tuple(msg.value))
        if max_records and i>=max_records: break
    cons.commit(); cons.close()
    if not rows: print("rien à insérer"); return 0
    with psycopg2.connect(**PG_CONN) as conn:
        execute_batch(conn.cursor(), SQL, rows); conn.commit()
    print(f"✅ {len(rows)} lignes insérées dans {TABLE_TRANS}")
    return len(rows)

if __name__ == "__main__":
    insert_from_kafka(run_id="debug")




