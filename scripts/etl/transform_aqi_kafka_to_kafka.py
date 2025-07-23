from __future__ import annotations
import json, os
from typing import Dict, Optional
from kafka import KafkaConsumer, KafkaProducer

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
TOPIC_RAW  = os.getenv("TOPIC_AQI_RAW", "aqi_current")
TOPIC_OUT  = os.getenv("TOPIC_AQI_TRANSFORMED", "aqi_transformed")

KEEP = {
    "run_id","time","city","latitude","longitude",
    "european_aqi","pm2_5","pm10","carbon_monoxide",
    "sulphur_dioxide","uv_index",
}

def transform_record(rec: Dict[str, object]) -> Dict[str, object]:
    return {k: rec.get(k) for k in KEEP}

def transform_kafka_raw_to_transformed(run_id: str,
                                       max_records: Optional[int]=None) -> int:
    cons = KafkaConsumer(
        TOPIC_RAW, bootstrap_servers=KAFKA_BROKER,
        auto_offset_reset="earliest", enable_auto_commit=True,
        group_id="aqi_transform_consumer", consumer_timeout_ms=10000,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
    )
    prod = KafkaProducer(
        bootstrap_servers=KAFKA_BROKER,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    sent = 0
    for i,msg in enumerate(cons,1):
        if msg.value.get("run_id") != run_id:
            continue
        prod.send(TOPIC_OUT, transform_record(msg.value)); sent += 1
        if max_records and i>=max_records: break
    cons.close(); prod.flush(); prod.close()
    print(f"✅ {sent} messages transformés → {TOPIC_OUT}")
    return sent

if __name__ == "__main__":
    transform_kafka_raw_to_transformed(run_id="debug")
