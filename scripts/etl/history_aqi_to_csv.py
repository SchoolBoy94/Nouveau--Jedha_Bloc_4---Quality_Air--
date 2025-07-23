# #!/usr/bin/env python3
# # scripts/fetch_aqi_history.py
# # ---------------------------------------------------------------------
# # Ex. :  python fetch_aqi_history.py --lat 52.52 --lon 13.41 \
# #                               --start 2025-07-11 --end 2025-07-23 \
# #                               --out berlin_aqi.csv
# # ---------------------------------------------------------------------

# from __future__ import annotations

# import argparse
# import csv
# from datetime import datetime
# from pathlib import Path
# from typing import List

# import openmeteo_requests
# import pandas as pd
# import requests_cache
# from retry_requests import retry

# AQI_VARS: List[str] = [
#     "european_aqi", "pm10", "pm2_5", "carbon_monoxide", "nitrogen_dioxide",
#     "sulphur_dioxide", "ozone", "ammonia", "uv_index_clear_sky", "uv_index",
#     "dust", "aerosol_optical_depth", "alder_pollen", "birch_pollen",
#     "grass_pollen", "mugwort_pollen", "olive_pollen", "ragweed_pollen",
# ]

# URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

# # ---------- Open‑Meteo client (cache + retry) -------------------------
# cache_session = requests_cache.CachedSession(".cache_aqi_hist", expire_after=3600)
# session = retry(cache_session, retries=5, backoff_factor=0.2)
# openmeteo = openmeteo_requests.Client(session=session)


# def fetch_history(lat: float, lon: float, start: str, end: str) -> pd.DataFrame:
#     """Retourne un DataFrame AQI horaire entre *start* et *end* inclus."""
#     params = {
#         "latitude": lat,
#         "longitude": lon,
#         "hourly": ",".join(AQI_VARS),
#         "start_date": start,
#         "end_date": end,
#         "timezone": "UTC",
#     }
#     resp = openmeteo.weather_api(URL, params=params)[0]  # une seule localisation
#     hourly = resp.Hourly()

#     index = pd.date_range(
#         start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
#         end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
#         freq=pd.Timedelta(seconds=hourly.Interval()),
#         inclusive="left",
#     )

#     data = {"time": index}
#     for i, var in enumerate(AQI_VARS):
#         data[var] = hourly.Variables(i).ValuesAsNumpy()

#     return pd.DataFrame(data)


# def main() -> None:
#     p = argparse.ArgumentParser(description="Télécharge l’historique AQI horaire")
#     p.add_argument("--lat",  type=float, required=True, help="Latitude")
#     p.add_argument("--lon",  type=float, required=True, help="Longitude")
#     p.add_argument("--start", required=True, help="Date début (YYYY-MM-DD)")
#     p.add_argument("--end",   required=True, help="Date fin   (YYYY-MM-DD)")
#     p.add_argument("--out", default="aqi_history.csv", help="Chemin du CSV")
#     args = p.parse_args()

#     # Vérifie le format des dates
#     for d in (args.start, args.end):
#         datetime.strptime(d, "%Y-%m-%d")  # lève ValueError si format invalide

#     df = fetch_history(args.lat, args.lon, args.start, args.end)
#     if df.empty:
#         print("⚠️  Aucun enregistrement retourné.")
#         return

#     out_path = Path(args.out)
#     df.to_csv(out_path, index=False, quoting=csv.QUOTE_NONNUMERIC)
#     print(f"✓ {len(df)} lignes écrites dans {out_path.resolve()}")


# if __name__ == "__main__":
#     main()






import os, json, csv
import pandas as pd
import requests_cache
from datetime import datetime
from pathlib import Path
from typing import List
import argparse
from retry_requests import retry
import openmeteo_requests

# ─── Config ─────────────────────────────────────────
CITIES_FILE = os.getenv("CITIES_FILE", "/opt/airflow/data/cities.json")
AQI_VARS: List[str] = [
    "european_aqi", "pm10", "pm2_5", "carbon_monoxide", "nitrogen_dioxide",
    "sulphur_dioxide", "ozone", "ammonia", "uv_index_clear_sky", "uv_index",
    "dust", "aerosol_optical_depth", "alder_pollen", "birch_pollen",
    "grass_pollen", "mugwort_pollen", "olive_pollen", "ragweed_pollen",
]
URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

# ─── Open-Meteo client ─────────────────────────────
cache_session = requests_cache.CachedSession(".cache_aqi_hist", expire_after=3600)
session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=session)

# ─── Load cities ───────────────────────────────────
def _load_cities() -> List[dict]:
    if not os.path.exists(CITIES_FILE):
        raise FileNotFoundError(f"❌ {CITIES_FILE} introuvable")
    return json.load(open(CITIES_FILE, "r", encoding="utf-8"))

# ─── Fetch AQI history for a location ──────────────
def fetch_history(lat: float, lon: float, start: str, end: str) -> pd.DataFrame:
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ",".join(AQI_VARS),
        "start_date": start,
        "end_date": end,
        "timezone": "UTC",
    }
    resp = openmeteo.weather_api(URL, params=params)[0]
    hourly = resp.Hourly()

    index = pd.date_range(
        start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
        end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
        freq=pd.Timedelta(seconds=hourly.Interval()),
        inclusive="left",
    )

    data = {"time": index}
    for i, var in enumerate(AQI_VARS):
        data[var] = hourly.Variables(i).ValuesAsNumpy()

    return pd.DataFrame(data)

# ─── Main ──────────────────────────────────────────
def main() -> None:
    p = argparse.ArgumentParser(description="Télécharge l’historique AQI pour plusieurs villes")
    p.add_argument("--start", required=True, help="Date début (YYYY-MM-DD)")
    p.add_argument("--end",   required=True, help="Date fin   (YYYY-MM-DD)")
    p.add_argument("--out", default="aqi_history_all_cities.csv", help="Fichier CSV de sortie")
    args = p.parse_args()

    # Valide le format des dates
    for d in (args.start, args.end):
        datetime.strptime(d, "%Y-%m-%d")

    cities = _load_cities()
    all_dataframes = []

    for city in cities:
        print(f"⏳ Traitement de {city['name']}...")
        try:
            df = fetch_history(city["lat"], city["lon"], args.start, args.end)
        except Exception as e:
            print(f"❌ Erreur pour {city['name']}: {e}")
            continue

        if df.empty:
            print(f"⚠️  Données vides pour {city['name']}")
            continue

        df.insert(1, "city", city["name"])
        df.insert(2, "latitude", city["lat"])
        df.insert(3, "longitude", city["lon"])
        all_dataframes.append(df)

    if not all_dataframes:
        print("❌ Aucune donnée récupérée.")
        return

    final_df = pd.concat(all_dataframes, ignore_index=True)
    final_df.to_csv(args.out, index=False, quoting=csv.QUOTE_NONNUMERIC)
    print(f"✅ {len(final_df)} lignes enregistrées dans {Path(args.out).resolve()}")

if __name__ == "__main__":
    main()
