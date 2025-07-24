# ------------------------------------------------------------------
# 1.  Charge `aqi_transform`
# 2.  Garde les 24 h les plus récentes, sample 20 %
# 3.  RandomizedSearch LightGBM (30 tirages)
# 4.  Log du modèle dans MLflow + promotion vers Staging
# ------------------------------------------------------------------

import os, numpy as np, pandas as pd
from sqlalchemy import create_engine
import re


from sklearn.model_selection import (
    train_test_split, RandomizedSearchCV, KFold
)
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import FunctionTransformer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error, r2_score
from scipy.stats import randint, uniform
from lightgbm import LGBMRegressor

# 🔗----------------- MLflow -------------------------------------------------
import mlflow, mlflow.sklearn
from mlflow.tracking import MlflowClient
from pathlib import Path
# csv_path = Path(__file__).parent / "aqi_2024.csv"

# Aller deux dossiers au-dessus, puis vers 'etl'
csv_path = Path(__file__).parent.parent / "etl" / "aqi_2024.csv"


MLFLOW_URI      = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
EXPERIMENT_NAME = os.getenv("MLFLOW_EXPERIMENT",    "aqi_prediction")
TARGET_NAME     = "european_aqi"
REGISTERED_NAME = f"lgbm_{TARGET_NAME}"
# ---------------------------------------------------------------------------

# PG_CONN_STR = os.getenv(
#     "PG_CONN_STR",
#     "postgresql+psycopg2://postgres:postgres@postgres:5432/aqi",
# )
# engine = create_engine(PG_CONN_STR)
# df = pd.read_sql("SELECT * FROM aqi_transform", engine)

df = pd.read_csv(csv_path, skiprows=2)
df.columns = [re.sub(r"\s*\(.*?\)", "", col).strip().lower() for col in df.columns]

print("✅ Colonnes disponibles :", df.columns.tolist())

# # Tentative de renommage si nécessaire
# if "main.aqi" in df.columns:
#     df.rename(columns={"main.aqi": "european_aqi"}, inplace=True)


# ---------- 1. Fenêtre 24 h + sample 20 % ----------------------------------
df["time"] = pd.to_datetime(df["time"], utc=True, errors="coerce")
latest_ts    = df["time"].max()

# recent_df    = df[df["time"] >= latest_ts - pd.Timedelta(days=1)]
recent_df = df[df["time"] >= latest_ts - pd.DateOffset(months=6)]


df_1 = recent_df.sample(frac=0.30, random_state=42)

print(f"🎯 {len(df_1)} lignes sélectionnées dans la fenêtre "
      f"{(latest_ts-pd.Timedelta(days=1)).strftime('%F %H:%M')} → "
      f"{latest_ts.strftime('%F %H:%M')}")

# ---------- 2. Séparation features / cible ---------------------------------
y = df_1[TARGET_NAME]
X = df_1.drop(columns=[TARGET_NAME, "time"])

pollutants = ["pm2_5", "pm10", "carbon_monoxide",
              "sulphur_dioxide", "uv_index"]

# ---------- 3. Pré‑traitement ----------------------------------------------
log_transform = FunctionTransformer(lambda x: np.log10(x + 1))

preprocess = ColumnTransformer(
    [
        ("log", Pipeline([
            ("imp", SimpleImputer(strategy="median")),
            ("log", log_transform),
        ]), pollutants),

        ("num", SimpleImputer(strategy="median"),
         list(set(X.columns) - set(pollutants))),
    ],
    remainder="drop",
)

# # ---------- 4. Hyper‑paramètres LGBM ---------------------------------------
# param_dist = {
#     "num_leaves":        randint(20, 96),
#     "learning_rate":     uniform(0.02, 0.12),
#     "n_estimators":      randint(300, 900),
#     "subsample":         uniform(0.7, 0.25),
#     "colsample_bytree":  uniform(0.7, 0.25),
#     "min_child_samples": randint(10, 60),
#     "reg_alpha":         uniform(0.0, 0.5),
#     "reg_lambda":        uniform(0.0, 0.8),
# }

# base_lgbm = LGBMRegressor(
#     objective="regression",
#     metric="l1",
#     early_stopping_rounds=50, # Delete This Part
#     random_state=42,
#     verbose=-1,
# )

# search = RandomizedSearchCV(
#     base_lgbm, param_dist, n_iter=30,
#     scoring="neg_mean_absolute_error",
#     cv=KFold(3, shuffle=True, random_state=42),
#     n_jobs=-1, random_state=42, verbose=0,
# )

# pipe = Pipeline([("prep", preprocess), ("model", search)])

# # ---------- 5. Entraînement + MLflow ---------------------------------------
# X_tr, X_val, y_tr, y_val = train_test_split(
#     X, y, test_size=0.2, random_state=42, shuffle=True
# )

# mlflow.set_tracking_uri(MLFLOW_URI)
# mlflow.set_experiment(EXPERIMENT_NAME)
# client = MlflowClient()

# with mlflow.start_run(run_name="lgbm_aqi") as run:
#     # params ≈ taille + search cfg
#     mlflow.log_param("sample_rows", len(df_1))
#     mlflow.log_param("rand_iter",   30)

#     pipe.fit(X_tr, y_tr)

#     best_params = search.best_params_
#     mlflow.log_params(best_params)

#     pred = pipe.predict(X_val)
#     mae  = mean_absolute_error(y_val, pred)
#     r2   = r2_score(y_val, pred)

#     mlflow.log_metric("MAE_holdout", mae)
#     mlflow.log_metric("R2_holdout",  r2)

#     mlflow.sklearn.log_model(
#         sk_model=pipe,
#         artifact_path="model",
#         registered_model_name=REGISTERED_NAME,
#     )

#     print(f"🏆  Best CV‑MAE = {-search.best_score_:.4f}")
#     print(f"🔍 Hold‑out MAE = {mae:.4f} | R² = {r2:.3f}")

#     # ---------- Promotion en Staging --------------------------------------
#     versions = client.get_latest_versions(REGISTERED_NAME, stages=["None"])
#     if versions:
#         latest = max(versions, key=lambda v: int(v.version))
#         client.transition_model_version_stage(
#             name=REGISTERED_NAME,
#             version=latest.version,
#             stage="Staging",
#             archive_existing_versions=False,
#         )
#         print(f"🚀 Modèle v{latest.version} promu → Staging")
#     else:
#         print("⚠️  Aucun nouveau modèle à promouvoir.")



#       DIRECT
# ---------- 4. Modèle LightGBM sans recherche d’hyper‑paramètres ----------
lgbm_params = {
    "objective":          "regression",
    "metric":             "l1",          # MAE
    "n_estimators":       600,
    "learning_rate":      0.05,
    "num_leaves":         63,
    "subsample":          0.8,
    "colsample_bytree":   0.8,
    "random_state":       42,
    "verbose":            -1,
}

model = LGBMRegressor(**lgbm_params)

pipe = Pipeline([
    ("prep", preprocess),
    ("model", model),
])

# ---------- 5. Entraînement + log MLflow ----------------------------------
X_tr, X_val, y_tr, y_val = train_test_split(
    X, y, test_size=0.2, shuffle=True, random_state=42
)

mlflow.set_tracking_uri(MLFLOW_URI)
mlflow.set_experiment(EXPERIMENT_NAME)
client = MlflowClient()

with mlflow.start_run(run_name="lgbm_aqi_fixed") as run:

    # log des infos de dataset et des hyper‑paramètres fixés
    mlflow.log_param("sample_rows", len(df_1))
    mlflow.log_params(lgbm_params)

    pipe.fit(X_tr, y_tr)

    pred = pipe.predict(X_val)
    mae  = mean_absolute_error(y_val, pred)
    r2   = r2_score(y_val, pred)

    mlflow.log_metric("MAE_holdout", mae)
    mlflow.log_metric("R2_holdout",  r2)

    mlflow.sklearn.log_model(
        sk_model=pipe,
        artifact_path="model",
        registered_model_name=REGISTERED_NAME,
    )

    print(f"🔍 Hold‑out MAE = {mae:.4f} | R² = {r2:.3f}")

    # -------- Promotion en Staging ---------------------------------------
    versions = client.get_latest_versions(REGISTERED_NAME, stages=["None"])
    if versions:
        latest = max(versions, key=lambda v: int(v.version))
        client.transition_model_version_stage(
            name=REGISTERED_NAME,
            version=latest.version,
            stage="Staging",
            archive_existing_versions=False,
        )
        print(f"🚀 Modèle v{latest.version} promu → Staging")
    else:
        print("⚠️  Aucun nouveau modèle à promouvoir.")
