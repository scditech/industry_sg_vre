"""DashboardPiece implementation for Domino. Same pattern as KPIPiece/BatterySimPiece: logic and pandas in piece.py only."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from domino.base_piece import BasePiece

from .models import FILE_SPECS, InputModel, OutputModel

SCENARIO_COLUMNS = ["scenario", "scenario_name", "case", "variant"]


def _safe_read_table(path_value: str | None, file_format: str | None = None) -> tuple[pd.DataFrame, str | None]:
    if not path_value:
        return pd.DataFrame(), "file path not provided"
    file_path = Path(path_value)
    if not file_path.is_file():
        return pd.DataFrame(), f"file not found: {path_value}"
    inferred = (file_format or file_path.suffix.lstrip(".")).lower()
    try:
        df = pd.read_parquet(file_path) if inferred == "parquet" else pd.read_csv(file_path)
    except Exception as exc:
        return pd.DataFrame(), f"failed to parse {inferred}: {exc}"
    for col in ("datetime", "timestamp", "date_time", "time"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df, None


def _dataframe_to_json_rows(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df.empty:
        return []
    out = df.copy()
    for c in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[c]):
            out[c] = out[c].dt.strftime("%Y-%m-%dT%H:%M:%S")
    out = out.where(pd.notnull(out), None)
    return out.to_dict(orient="records")


def _extract_scenarios(*dfs: pd.DataFrame) -> list[str]:
    scenarios: set[str] = set()
    for df in dfs:
        if df.empty:
            continue
        lower = {c.lower(): c for c in df.columns}
        for sc in SCENARIO_COLUMNS:
            if sc in lower:
                vals = df[lower[sc]].dropna().astype(str).str.strip()
                scenarios.update(v for v in vals if v)
                break
    return sorted(scenarios)


class DashboardPiece(BasePiece):
    """Collects optional CSVs/parquet and writes dashboard_data.json. Same structure as other pieces."""

    def piece_function(self, input_data: InputModel) -> OutputModel:
        print("\n[INFO] ===== DASHBOARD PIECE START =====")
        logger = getattr(self, "logger", None)
        if logger:
            logger.info("DashboardPiece started")

        results_dir = getattr(self, "results_path", None) or "."
        output_path = Path(results_dir) / "dashboard_data.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        datasets: dict[str, object] = {spec["dataset_key"]: [] for spec in FILE_SPECS.values()}
        input_status: dict[str, dict[str, object]] = {}
        parsed_frames: dict[str, pd.DataFrame] = {}

        for input_field, spec in FILE_SPECS.items():
            dataset_key = spec["dataset_key"]
            path_value = getattr(input_data, input_field, None)
            frame, error = _safe_read_table(path_value, spec.get("file_format"))

            datasets[dataset_key] = _dataframe_to_json_rows(frame)
            parsed_frames[dataset_key] = frame
            input_status[input_field] = {
                "provided": error is None,
                "path": path_value,
                "default_filename": spec["default_path"],
                "source_piece": spec["source_piece"],
                "file_format": spec["file_format"],
                "rows": int(len(frame.index)) if error is None else 0,
                "error": error,
            }

        scenarios = _extract_scenarios(
            parsed_frames.get("preprocess_predict"),
            parsed_frames.get("predict_predictions"),
            parsed_frames.get("simulate_results"),
            parsed_frames.get("kpi_results"),
            parsed_frames.get("investment_evaluation"),
        )
        if not scenarios:
            scenarios = ["Default"]

        payload = {
            "meta": {
                "piece": "DashboardPiece",
                "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            },
            "inputs": input_status,
            "scenarios": scenarios,
            "default_scenario": scenarios[0],
            "datasets": datasets,
        }

        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
        print(f"[INFO] Dashboard data written to {output_path}")
        if logger:
            logger.info("Dashboard data JSON written to %s", str(output_path))

        self.display_result = {"file_type": "json", "file_path": str(output_path)}
        return OutputModel(dashboard_data_json=str(output_path))
