# ------------------------------------------------------------------
# • Charge un hold‑out dans aqi_2024.csv
# • Évalue la dernière version “Staging” du modèle LightGBM AQI
# • Compare à l’éventuelle version “Production”
# • Promeut en Production si la MAE est plus basse
# ------------------------------------------------------------------

from __future__ import annotations
import os, sys, argparse, re
from datetime import timedelta
from pathlib import Path

import pandas as pd
from sklearn.metrics import mean_absolute_error
import mlflow
from mlflow.tracking import MlflowClient

# ---------------------- Configuration --------------------------------------
CSV_PATH       = Path(os.getenv("AQI_CSV_PATH",
                          Path(__file__).parent / "aqi_2024.csv"))
MLFLOW_URI      = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
EXPERIMENT_NAME = os.getenv("MLFLOW_EXPERIMENT",  "aqi_prediction")
TARGET          = "european_aqi"
MODEL_NAME      = f"lgbm_{TARGET}"
HOLDOUT_DAYS    = 7            # fenêtre par défaut (exclut les 24 h les + récentes)
# ---------------------------------------------------------------------------


def _load_and_clean_csv(path: Path) -> pd.DataFrame:
    """Lit le CSV (skiprows=2) en appliquant
       le même nettoyage de colonnes que dans train_aqi.py."""
    if not path.exists():
        sys.exit(f"❌  Dataset introuvable : {path}")

    df = pd.read_csv(path, skiprows=2)
    df.columns = [re.sub(r"\s*\(.*?\)", "", c).strip().lower() for c in df.columns]
    df["time"] = pd.to_datetime(df["time"], utc=True, errors="coerce")
    return df


def load_holdout(days: int) -> tuple[pd.DataFrame, pd.Series]:
    """Renvoie X_hold, y_hold construits comme dans le training."""
    df      = _load_and_clean_csv(CSV_PATH)
    latest  = df["time"].max()
    start   = latest - timedelta(days=days)
    end     = latest - timedelta(hours=24)      # on écarte le dernier jour
    holdout = df[(df["time"] > start) & (df["time"] <= end)]

    if holdout.empty:
        sys.exit("❌  Aucune donnée dans la fenêtre hold‑out.")

    y = holdout[TARGET]
    X = holdout.drop(columns=[TARGET, "time"])          # même logique que train_aqi.py
    print(f"📦  Hold‑out : {len(holdout)} lignes  "
          f"({start:%F} → {end:%F}) | cible : {TARGET}")
    return X, y


def evaluate_and_promote(days: int):
    mlflow.set_tracking_uri(MLFLOW_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)
    client = MlflowClient()

    # ---- 1️⃣  récupérer la version Staging ---------------------------------
    staging_vs = client.get_latest_versions(MODEL_NAME, stages=["Staging"])
    if not staging_vs:
        sys.exit(f"❌  Aucun modèle « {MODEL_NAME} » en Staging.")
    st_v = staging_vs[0]
    print(f"🔍  Staging → v{st_v.version} (run {st_v.run_id})")

    # ---- 2️⃣  hold‑out + évaluation ----------------------------------------
    X_hold, y_hold = load_holdout(days)
    st_model = mlflow.pyfunc.load_model(f"runs:/{st_v.run_id}/model")
    mae_st   = mean_absolute_error(y_hold, st_model.predict(X_hold))
    print(f"• MAE Staging  v{st_v.version} = {mae_st:.4f}")

    # ---- 3️⃣  Production (s’il y en a une) ---------------------------------
    prod_vs = client.get_latest_versions(MODEL_NAME, stages=["Production"])
    if prod_vs:
        pr_v   = prod_vs[0]
        mae_pr = client.get_run(pr_v.run_id).data.metrics.get("MAE_holdout")
        print(f"• MAE Production v{pr_v.version} = {mae_pr:.4f}")
    else:
        mae_pr = None
        print("• Pas de version Production existante.")

    # ---- 4️⃣  Promotion si meilleur ----------------------------------------
    if mae_pr is None or mae_st < mae_pr:
        client.transition_model_version_stage(
            name=MODEL_NAME,
            version=st_v.version,
            stage="Production",
            archive_existing_versions=True,
        )
        print(f"✅  Modèle v{st_v.version} promu en Production 🚀")
    else:
        print("🚫  Pas de promotion : MAE Staging ≥ MAE Production")


# ---------------------- CLI -------------------------------------------------
if __name__ == "__main__":
    p = argparse.ArgumentParser("Validate & promote AQI model")
    p.add_argument("--days", type=int, default=HOLDOUT_DAYS,
                   help="Taille de la fenêtre hold‑out (jours, défaut : 7)")
    args = p.parse_args()
    evaluate_and_promote(args.days)
