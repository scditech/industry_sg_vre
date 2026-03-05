
from domino.base_piece import BasePiece
from .models import InputModel, OutputModel

import pandas as pd
from pathlib import Path
import joblib
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from datetime import datetime


class TrainModelPiece(BasePiece):

    def piece_function(self, input_data: InputModel) -> OutputModel:

        print("[INFO] TrainModelPiece started")
        print(f"[INFO] Using training data: {input_data.data_path}")

        data_path = Path(input_data.data_path)

        if not data_path.exists():
            raise FileNotFoundError(f"Training data not found: {data_path}")

        # ---- LOAD DATA ----
        if data_path.suffix == ".parquet":
            df = pd.read_parquet(data_path)
        else:
            df = pd.read_csv(data_path)

        if "datetime" not in df.columns:
            raise ValueError("Dataset must contain 'datetime' column")

        df["datetime"] = pd.to_datetime(df["datetime"])
        df = df.sort_values("datetime")

        target = "load_kw"
        if target not in df.columns:
            raise ValueError(f"Target column '{target}' not found")

        # =========================================================
        # SIMPLE FEATURES FOR SIMULATION MODEL
        # =========================================================
        print("[INFO] Creating time features")

        df["hour"] = df["datetime"].dt.hour
        df["dayofweek"] = df["datetime"].dt.dayofweek
        df["month"] = df["datetime"].dt.month

        # lag features
        print("[INFO] Creating lag features")
        df["lag_1"] = df[target].shift(1)
        df["lag_4"] = df[target].shift(4)

        df = df.dropna().reset_index(drop=True)

        # =========================================================
        # TRAIN / TEST SPLIT (simple time split)
        # =========================================================
        split_index = int(len(df) * 0.8)

        train_df = df.iloc[:split_index]
        test_df = df.iloc[split_index:]

        feature_cols = [c for c in df.columns if c not in ["datetime", target]]

        X_train = train_df[feature_cols]
        y_train = train_df[target]

        X_test = test_df[feature_cols]
        y_test = test_df[target]

        print(f"[INFO] Train rows: {len(X_train)}")
        print(f"[INFO] Test rows: {len(X_test)}")

        # =========================================================
        # TRAIN MODEL
        # =========================================================
        print("[INFO] Training XGBoost model")

        model = XGBRegressor(
            objective="reg:squarederror",
            learning_rate=0.05,
            max_depth=6,
            n_estimators=350,
            subsample=0.8,
            colsample_bytree=0.8
        )

        model.fit(X_train, y_train)

        # =========================================================
        # EVALUATION
        # =========================================================
        print("[INFO] Evaluating model")

        preds = model.predict(X_test)

        mae = mean_absolute_error(y_test, preds)
        mse = mean_squared_error(y_test, preds)
        rmse = mse ** 0.5   # manual sqrt (fix for older sklearn)

        print(f"[METRIC] MAE: {mae:.2f}")
        print(f"[METRIC] RMSE: {rmse:.2f}")

        # =========================================================
        # SAVE MODEL
        # =========================================================
        model_path = Path(self.results_path) / "xgboost_model.pkl"
        log_path = Path(self.results_path) / "training_log.txt"

        joblib.dump(model, model_path)

        with open(log_path, "w") as f:
            f.write(f"Training time (UTC): {datetime.utcnow()}\n")
            f.write(f"Rows total: {len(df)}\n")
            f.write(f"Train rows: {len(train_df)}\n")
            f.write(f"Test rows: {len(test_df)}\n")
            f.write(f"Features: {feature_cols}\n")
            f.write(f"MAE: {mae:.4f}\n")
            f.write(f"RMSE: {rmse:.4f}\n")

        print(f"[SUCCESS] Model saved to {model_path}")

        return OutputModel(
            message=f"Model trained. MAE={mae:.2f}, RMSE={rmse:.2f}",
            model_file_path=str(model_path),
            train_log_path=str(log_path)
        )
