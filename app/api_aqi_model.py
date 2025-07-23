# # api_aqi_model.py
# # ---------------------------------------------------------------------------
# # 1.  Au démarrage : récupère la version "Production" du modèle enregistré
# #     dans le MLflow Model Registry et la charge en mémoire.
# # 2.  Expose deux routes :
# #     • GET  /health         → simple ping
# #     • POST /predict        → prédictions AQI pour 1…N enregistrements
# # ---------------------------------------------------------------------------

# from __future__ import annotations
# import os, sys
# from typing import List

# import mlflow
# from mlflow.tracking import MlflowClient
# import pandas as pd
# from pydantic import BaseModel, Field, conlist
# from fastapi import FastAPI, HTTPException

# # --------------------------- Configuration ----------------------------------
# MLFLOW_URI  = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
# MODEL_NAME  = os.getenv("AQI_MODEL_NAME",       "lgbm_european_aqi")
# STAGE       = os.getenv("AQI_MODEL_STAGE",      "Production")   # ou "Staging"

# mlflow.set_tracking_uri(MLFLOW_URI)
# client = MlflowClient()

# # --------------------------- Chargement modèle ------------------------------
# def _load_production_model():
#     """
#     Récupère la dernière version MLflow au stage voulu et retourne
#     un modèle pyfunc prêt à l’emploi.
#     """
#     versions = client.get_latest_versions(MODEL_NAME, stages=[STAGE])
#     if not versions:
#         sys.exit(f"❌  Aucun modèle {MODEL_NAME} en stage “{STAGE}”.")
#     mv = versions[0]
#     print(f"📦  Loading {MODEL_NAME} v{mv.version} ({STAGE})")
#     return mlflow.pyfunc.load_model(f"models:/{MODEL_NAME}/{STAGE}")

# model = _load_production_model()

# # --------------------------- Schéma d’entrée --------------------------------
# NUM_FEATURES = [
#     "pm2_5", "pm10", "carbon_monoxide", "sulphur_dioxide", "uv_index",
# ]

# class AQIRecord(BaseModel):
#     # Les features nécessaires au pipeline (names = colonnes features.csv)
#     pm2_5:            float = Field(..., example=5.8)
#     pm10:             float = Field(..., example=9.5)
#     carbon_monoxide:  float = Field(..., example=130.0)
#     sulphur_dioxide:  float = Field(..., example=0.8)
#     uv_index:         float = Field(..., example=0.0)

# class AQIBatch(BaseModel):
#     records: conlist(AQIRecord, min_items=1)

# # --------------------------- FastAPI ----------------------------------------
# app = FastAPI(
#     title="AQI Prediction API",
#     description="Prédis *european_aqi* à partir des polluants clés.",
#     version="1.0.0",
# )

# # @app.get("/health", tags=["System"])
# # def health():
# #     """Vérifie que l’API et le modèle sont chargés."""
# #     return {"status": "ok", "model_stage": STAGE}


# @app.get("/health")
# def health():
#     return {"status": "ok", "model_stage": "Production"}

# @app.post("/predict", tags=["Inference"])
# def predict(batch: AQIBatch):
#     """Retourne un european_aqi par enregistrement."""
#     try:
#         # Pydantic → DataFrame (ordonnons les colonnes)
#         df = pd.DataFrame([r.dict() for r in batch.records])[NUM_FEATURES]
#         preds = model.predict(df)
#         return {"european_aqi": preds.tolist()}
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))

# # ---------------------------------------------------------------------------
# # Lancement :
# #   uvicorn api_aqi_model:app --host 0.0.0.0 --port 8000 --reload
# # ---------------------------------------------------------------------------









# import os
# from typing import Any, Dict, List

# import pandas as pd
# import mlflow.pyfunc
# from fastapi import FastAPI, HTTPException
# from pydantic import BaseModel

# # ─── Configuration ───────────────────────────────────────────────────────────
# MODEL_NAME  = os.getenv("AQI_MODEL_NAME", "lgbm_european_aqi")
# MODEL_STAGE = os.getenv("AQI_MODEL_STAGE", "Production")
# MLFLOW_URI  = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
# MODEL_URI   = f"models:/{MODEL_NAME}/{MODEL_STAGE}"

# mlflow.set_tracking_uri(MLFLOW_URI)

# # ─── Chargement du modèle MLflow ─────────────────────────────────────────────
# # try:
# #     model = mlflow.pyfunc.load_model(MODEL_URI)
# # except Exception as e:
# #     raise RuntimeError(f"❌ Impossible de charger le modèle {MODEL_URI}: {e}")


# def load_model():
#     try:
#         return mlflow.pyfunc.load_model(MODEL_URI)
#     except Exception as e:
#         raise RuntimeError(f"❌ Impossible de charger le modèle {MODEL_URI}: {e}")

# model = load_model()  # Chargement initial


# # ─── Colonnes attendues (ordre important !) ──────────────────────────────────
# FEATURE_COLUMNS: List[str] = [
#     "pm2_5", "pm10", "carbon_monoxide", "sulphur_dioxide", "uv_index"
# ]

# # ─── Application FastAPI ─────────────────────────────────────────────────────
# app = FastAPI(
#     title="AQI Prediction API",
#     description="Prédit le European AQI à partir des polluants.",
#     version="1.0.0",
# )

# # ─── Schémas Pydantic ────────────────────────────────────────────────────────
# class PredictRequest(BaseModel):
#     data: Dict[str, Any]

# class PredictResponse(BaseModel):
#     european_aqi: float

# # ─── Endpoint de prédiction ──────────────────────────────────────────────────
# @app.post("/predict", response_model=PredictResponse)
# def predict(req: PredictRequest):
#     try:
#         df = pd.DataFrame([req.data])
#         missing = [col for col in FEATURE_COLUMNS if col not in df.columns]
#         if missing:
#             raise HTTPException(status_code=422, detail=f"Colonnes manquantes : {missing}")
#         df = df[FEATURE_COLUMNS]
#         preds = model.predict(df)
#         return PredictResponse(european_aqi=float(preds[0]))
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=f"Erreur lors de la prédiction : {e}")

# # ─── Health check ────────────────────────────────────────────────────────────
# @app.get("/health")
# def health():
#     return {"status": "ok", "model_uri": MODEL_URI}

# # ─── Endpoint de rechargement du modèle ──────────────────────────────────────
# @app.get("/reload")
# def reload_model():
#     global model
#     try:
#         model = load_model()
#         return {"message": f"✅ Modèle rechargé depuis {MODEL_URI}"}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Erreur de rechargement : {e}")










import os
from typing import Any, Dict, List, Union

import pandas as pd
import mlflow.pyfunc
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# ─── Configuration ───────────────────────────────────────────────────────────
MODEL_NAME  = os.getenv("AQI_MODEL_NAME", "lgbm_european_aqi")
MODEL_STAGE = os.getenv("AQI_MODEL_STAGE", "Production")
MLFLOW_URI  = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
MODEL_URI   = f"models:/{MODEL_NAME}/{MODEL_STAGE}"

mlflow.set_tracking_uri(MLFLOW_URI)

def load_model():
    try:
        return mlflow.pyfunc.load_model(MODEL_URI)
    except Exception as e:
        raise RuntimeError(f"❌ Impossible de charger le modèle {MODEL_URI}: {e}")

model = load_model()

FEATURE_COLUMNS: List[str] = [
    "pm2_5", "pm10", "carbon_monoxide", "sulphur_dioxide", "uv_index"
]

app = FastAPI(
    title="AQI Prediction API",
    description="Prédit le European AQI à partir des polluants.",
    version="1.0.0",
)

# ─── Schémas Pydantic ────────────────────────────────────────────────────────
class PredictRequest(BaseModel):
    data: Union[Dict[str, Any], List[Dict[str, Any]]]

class PredictResponseSingle(BaseModel):
    european_aqi: float

class PredictResponseBatch(BaseModel):
    predictions: List[float]

# ─── Endpoint de prédiction ──────────────────────────────────────────────────
@app.post("/predict", response_model=Union[PredictResponseSingle, PredictResponseBatch])
def predict(req: PredictRequest):
    try:
        # Gestion mono vs multi
        if isinstance(req.data, list):
            df = pd.DataFrame(req.data)
        else:
            df = pd.DataFrame([req.data])

        # Validation colonnes
        missing = [col for col in FEATURE_COLUMNS if col not in df.columns]
        if missing:
            raise HTTPException(status_code=422, detail=f"Colonnes manquantes : {missing}")

        df = df[FEATURE_COLUMNS]
        preds = model.predict(df)

        # Mono ou multi
        if len(preds) == 1:
            return PredictResponseSingle(european_aqi=float(preds[0]))
        else:
            return PredictResponseBatch(predictions=[float(p) for p in preds])

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erreur lors de la prédiction : {e}")

# ─── Health check ────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "model_uri": MODEL_URI}

@app.get("/reload")
def reload_model():
    global model
    try:
        model = load_model()
        return {"message": f"✅ Modèle rechargé depuis {MODEL_URI}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur de rechargement : {e}")
