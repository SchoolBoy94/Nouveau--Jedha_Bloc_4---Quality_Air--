import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import re
import pandas as pd
import mlflow.pyfunc
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset, RegressionPreset
from evidently.ui.workspace import Workspace


csv_path = Path(__file__).parent / "aqi_2024.csv"
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
MODEL_URI           = os.getenv("MLFLOW_MODEL_URI", "models:/lgbm_european_aqi/Production")

WORKSPACE_PATH      = Path(os.getenv("EVIDENTLY_WORKSPACE_PATH", "/workspace"))
PROJECT_NAME        = "AQI monitoring"
HOLDOUT_DAYS        = int(os.getenv("EVIDENTLY_HOLDOUT_DAYS", "7"))


def load_slices(days: int):
    # if not FEATURES_PATH.exists():
    #     sys.exit(f"❌ Fichier introuvable : {FEATURES_PATH}")

    
    df = pd.read_csv(csv_path, skiprows=2)
    df.columns = [re.sub(r"\s*\(.*?\)", "", col).strip().lower() for col in df.columns]
    df["time"] = pd.to_datetime(df["time"], utc=True, errors="coerce")
    
    latest = df["time"].max()
    cutoff_ref = latest - timedelta(days=days + 1)

    reference = df[df["time"] <= cutoff_ref].copy()
    current   = df[(df["time"] > cutoff_ref) & (df["time"] <= latest)].copy()
    return reference, current


def push_snapshot_to_ui(report: Report) -> None:
    ws = Workspace.create(path=str(WORKSPACE_PATH))
    found = ws.search_project(PROJECT_NAME)
    project = found[0] if found else ws.create_project(PROJECT_NAME)
    ws.add_report(project.id, report)
    print(f"✓ Snapshot ajouté au projet « {PROJECT_NAME} »")


def timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M")


def main() -> None:
    ref_df, cur_df = load_slices(HOLDOUT_DAYS)

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    model = mlflow.pyfunc.load_model(MODEL_URI)

    feat_cols = ["pm2_5", "pm10", "carbon_monoxide", "sulphur_dioxide", "uv_index"]
    for df in (ref_df, cur_df):
        df["prediction"] = model.predict(df[feat_cols])
        df["target"]     = df["european_aqi"]

    report = Report(metrics=[DataDriftPreset(), RegressionPreset()])
    report.run(reference_data=ref_df, current_data=cur_df)

    push_snapshot_to_ui(report)

    ts = timestamp()
    html_path = WORKSPACE_PATH / f"drift-regression-report_{ts}.html"
    json_path = WORKSPACE_PATH / f"drift-regression-report_{ts}.json"

    report.save_html(str(html_path))
    report.save_json(str(json_path))

    print(f"✓ Rapports Evidently générés :\n   ├── {html_path}\n   └── {json_path}")


if __name__ == "__main__":
    main()
