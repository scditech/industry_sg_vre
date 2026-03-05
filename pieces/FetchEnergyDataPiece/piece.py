from domino.base_piece import BasePiece
from .models import InputModel, OutputModel
import pandas as pd
from pathlib import Path


class FetchEnergyDataPiece(BasePiece):
    """
    Load and merge energy CSV files from shared storage
    """

    def piece_function(self, input_data):
        # ---- START ----
        print("[INFO] FetchEnergyDataPiece started")

        print(f"[INFO] Load CSV: {input_data.load_csv}")
        print(f"[INFO] Production CSV: {input_data.production_csv}")
        print(f"[INFO] Prices CSV: {input_data.prices_csv}")

        load_csv = Path(input_data.load_csv)
        production_csv = Path(input_data.production_csv)
        prices_csv = Path(input_data.prices_csv)

        # ---- VALIDATE INPUT FILES ----
        for f in [load_csv, production_csv, prices_csv]:
            if not f.exists():
                message = f"File not found: {f}"
                print(f"[ERROR] {message}")
                return {
                    "message": message,
                    "output_path": ""
                }

        # ---- READ DATA ----
        print("[INFO] Reading CSV files")

        load_df = pd.read_csv(load_csv, parse_dates=["datetime"])
        production_df = pd.read_csv(production_csv, parse_dates=["datetime"])
        prices_df = pd.read_csv(prices_csv, parse_dates=["datetime"])

        # ---- MERGE ----
        print("[INFO] Merging data")

        load_df = load_df.set_index("datetime")
        production_df = production_df.set_index("datetime")
        prices_df = prices_df.set_index("datetime")

        merged_df = (
            load_df
            .join(production_df, how="outer")
            .join(prices_df, how="outer")
            .reset_index()
        )

        if "production_ton" in merged_df.columns:
            merged_df["production_ton"] = merged_df["production_ton"].ffill()

        if "price_eur_mwh" in merged_df.columns:
            merged_df["price_eur_mwh"] = merged_df["price_eur_mwh"].ffill()

        # ---- SAVE OUTPUT ----
        output_path = Path(self.results_path) / "merged_energy_data.parquet"
        merged_df.to_parquet(output_path, index=False)

        print(f"[SUCCESS] Data merged, rows: {len(merged_df)}")
        print(f"[SUCCESS] Output written to {output_path}")

        # ---- DOMINO UI OUTPUT ----
        self.display_result = {
            "file_type": "parquet",
            "file_path": str(output_path)
        }

        # ---- RETURN PLAIN DICT (CRITICAL) ----
        return {
            "message": f"Data merged successfully ({len(merged_df)} rows)",
            "output_path": str(output_path)
        }
