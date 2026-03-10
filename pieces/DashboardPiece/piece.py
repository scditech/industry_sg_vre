"""DashboardPiece implementation for Domino."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from domino.base_piece import BasePiece

from .models import (
    FILE_SPECS,
    InputModel,
    OutputModel,
    dataframe_to_json_rows,
    extract_scenarios,
    safe_read_table,
)


class DashboardPiece(BasePiece):
    """Collects optional CSVs and produces a single dashboard_data.json file."""

    def piece_function(self, input_data: InputModel) -> OutputModel:
        datasets: dict[str, object] = {
            spec["dataset_key"]: []
            for spec in FILE_SPECS.values()
        }
        input_status: dict[str, dict[str, object]] = {}
        parsed_frames = {}

        for input_field, spec in FILE_SPECS.items():
            dataset_key = spec["dataset_key"]
            path_value = getattr(input_data, input_field)
            frame, error = safe_read_table(path_value, spec.get("file_format"))

            datasets[dataset_key] = dataframe_to_json_rows(frame)

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

        scenarios = extract_scenarios(
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

        output_path = Path(self.results_path) / "dashboard_data.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))

        logger = getattr(self, "logger", None)
        if logger is not None:
            logger.info("Dashboard data JSON written to %s", str(output_path))

        self.display_result = {
            "file_type": "json",
            "file_path": str(output_path),
        }
        return OutputModel(dashboard_data_json=str(output_path))