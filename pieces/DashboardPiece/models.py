"""Data models and helper utilities for DashboardPiece and Streamlit app."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from pydantic import BaseModel, Field


FILE_SPECS = {
    "preprocess_predict_parquet": {
        "dataset_key": "preprocess_predict",
        "default_path": "predict_dataset_15min.parquet",
        "file_format": "parquet",
        "source_piece": "PreprocessEnergyDataPiece",
    },
    "predict_predictions_csv": {
        "dataset_key": "predict_predictions",
        "default_path": "predictions_15min.csv",
        "file_format": "csv",
        "source_piece": "PredictPiece",
    },
    "simulate_results_csv": {
        "dataset_key": "simulate_results",
        "default_path": "simulated_results.csv",
        "file_format": "csv",
        "source_piece": "SimulatePiece",
    },
    "simulate_summary_csv": {
        "dataset_key": "simulate_summary",
        "default_path": "summary.csv",
        "file_format": "csv",
        "source_piece": "SimulatePiece",
    },
    "kpi_results_csv": {
        "dataset_key": "kpi_results",
        "default_path": "kpi_results.csv",
        "file_format": "csv",
        "source_piece": "KPIPiece",
    },
    "investment_evaluation_csv": {
        "dataset_key": "investment_evaluation",
        "default_path": "investment_evaluation.csv",
        "file_format": "csv",
        "source_piece": "InvestmentEvalPiece",
    },
}

SCENARIO_COLUMNS = ["scenario", "scenario_name", "case", "variant"]


class InputModel(BaseModel):
    """DashboardPiece Input Model. All inputs optional; defaults point to shared_storage for Domino."""

    preprocess_predict_parquet: str | None = Field(
        default="/home/shared_storage/predict_dataset_15min.parquet",
        description="PreprocessEnergyDataPiece output: predict_dataset_15min.parquet.",
    )
    predict_predictions_csv: str | None = Field(
        default="/home/shared_storage/predictions_15min.csv",
        description="PredictPiece output: predictions_15min.csv.",
    )
    simulate_results_csv: str | None = Field(
        default="/home/shared_storage/simulated_results.csv",
        description="SimulatePiece output: simulated_results.csv.",
    )
    simulate_summary_csv: str | None = Field(
        default="/home/shared_storage/summary.csv",
        description="SimulatePiece output: summary.csv.",
    )
    kpi_results_csv: str | None = Field(
        default="/home/shared_storage/kpi_results.csv",
        description="KPIPiece output: kpi_results.csv.",
    )
    investment_evaluation_csv: str | None = Field(
        default="/home/shared_storage/investment_evaluation.csv",
        description="InvestmentEvalPiece output: investment_evaluation.csv.",
    )


class OutputModel(BaseModel):
    """DashboardPiece Output Model."""

    dashboard_data_json: str = Field(
        description="Path of dashboard consolidated JSON output.",
    )


def safe_read_table(path_value: str | None, file_format: str | None = None) -> tuple[pd.DataFrame, str | None]:
    """Read a CSV/parquet safely and return (DataFrame, error_message)."""
    if not path_value:
        return pd.DataFrame(), "file path not provided"

    file_path = Path(path_value)
    if not file_path.is_file():
        return pd.DataFrame(), f"file not found: {path_value}"

    inferred_format = (file_format or file_path.suffix.lstrip(".")).lower()

    try:
        if inferred_format == "parquet":
            df = pd.read_parquet(file_path)
        else:
            df = pd.read_csv(file_path)
    except Exception as exc:
        return pd.DataFrame(), f"failed to parse {inferred_format or 'table'}: {exc}"

    for candidate in ("datetime", "timestamp", "date_time", "time"):
        if candidate in df.columns:
            df[candidate] = pd.to_datetime(df[candidate], errors="coerce")

    return df, None


def dataframe_to_json_rows(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert DataFrame rows to JSON-safe dicts, including datetimes."""
    if df.empty:
        return []

    converted = df.copy()
    for column in converted.columns:
        if pd.api.types.is_datetime64_any_dtype(converted[column]):
            converted[column] = converted[column].dt.strftime("%Y-%m-%dT%H:%M:%S")

    converted = converted.where(pd.notnull(converted), None)
    return converted.to_dict(orient="records")


def extract_scenarios(*dfs: pd.DataFrame) -> list[str]:
    """Extract scenario names from any known scenario-like column."""
    scenarios: set[str] = set()
    for df in dfs:
        if df.empty:
            continue
        lower_map = {column.lower(): column for column in df.columns}
        for scenario_col in SCENARIO_COLUMNS:
            if scenario_col in lower_map:
                source_col = lower_map[scenario_col]
                values = df[source_col].dropna().astype(str).str.strip()
                scenarios.update(v for v in values if v)
                break

    return sorted(scenarios)