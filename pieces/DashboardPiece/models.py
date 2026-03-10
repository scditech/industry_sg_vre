"""Data models for DashboardPiece. No heavy deps so Domino can load Input/Output models without pandas."""
from __future__ import annotations

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
