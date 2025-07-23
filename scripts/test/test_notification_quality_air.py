from __future__ import annotations
import json, os, sys


from notifications.notif_quality_air import notify_if_poor

# Exemple de donnée polluante (PM2.5 > 25 µg/m³)
sample_record = {
    "city": "Paris",
    "time": "2025-07-20T15:00:00Z",
    "pm2_5": 42.3,
    "pm10": 80.1,
    "ozone": 100.0,  # pas en seuil "poor"
    "sulphur_dioxide": 900.0,  # seuil extremely poor
    "carbon_monoxide": 300.0,  # non concerné ici
}

notify_if_poor(sample_record)
