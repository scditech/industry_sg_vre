
from domino.base_piece import BasePiece
from .models import InputModel, OutputModel

import pandas as pd
from pathlib import Path
import joblib
from datetime import datetime


class PredictPiece(BasePiece):

    def piece_function(self, input_data: InputModel) -> OutputModel:

        print("[INFO] PredictPiece started")
        print(f"[INFO] Model path: {input_data.model_path}")
        print(f"[INFO] Data path: {input_data.data_path}")

        model_path = Path(input_data.model_path)
        data_path = Path(input_data.data_path)

        if not model_path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")

        if not data_path.exists():
            raise FileNotFoundError(f"Prediction data not found: {data_path}")

        # ---- LOAD MODEL ----
        model = joblib.load(model_path)

        # ---- LOAD DATA ----
        if data_path.suffix == ".parquet":
            df = pd.read_parquet(data_path)
        else:
            df = pd.read_csv(data_path)

        # =====================================================
        # FIX: sometimes datetime is index, not column
        # =====================================================
        if "datetime" not in df.columns:
            print("[WARN] datetime column not found, trying index reset")
            df = df.reset_index()

        if "datetime" not in df.columns:
            raise ValueError(
                f"Prediction dataset must contain datetime column. "
                f"Columns found: {df.columns.tolist()}"
            )

        df["datetime"] = pd.to_datetime(df["datetime"])
        df = df.sort_values("datetime").reset_index(drop=True)

        target = "load_kw"

        if target not in df.columns:
            raise ValueError(
                f"Prediction dataset must contain '{target}'. "
                f"Columns: {df.columns.tolist()}"
            )

        # =====================================================
        # SAME FEATURES AS TRAIN
        # =====================================================
        print("[INFO] Creating time features")

        df["hour"] = df["datetime"].dt.hour
        df["dayofweek"] = df["datetime"].dt.dayofweek
        df["month"] = df["datetime"].dt.month

        print("[INFO] Creating lag features")

        df["lag_1"] = df[target].shift(1)
        df["lag_4"] = df[target].shift(4)

        df = df.dropna().reset_index(drop=True)

        feature_names = model.get_booster().feature_names
        X = df[feature_names]

        # ---- PREDICT ----
        print("[INFO] Running prediction")
        preds = model.predict(X)

        df_out = df.copy()
        df_out["prediction_load_kw"] = preds

        # ---- SAVE CSV ----
        output_path = Path(self.results_path) / "predictions_15min.csv"
        df_out.to_csv(output_path, index=False)

        log_path = Path(self.results_path) / "prediction_log.txt"
        with open(log_path, "w") as f:
            f.write(f"Prediction time (UTC): {datetime.utcnow()}\n")
            f.write(f"Rows: {len(df_out)}\n")
            f.write(f"Features used: {feature_names}\n")
            f.write(f"Model: {model_path.name}\n")

        print("[SUCCESS] Prediction finished")
        print(f"[SUCCESS] Predictions saved to {output_path}")

        return OutputModel(
            message="Prediction finished successfully",
            prediction_file_path=str(output_path)
        )
