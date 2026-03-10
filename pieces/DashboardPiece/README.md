# DashboardPiece Quick Documentation

## Purpose
`DashboardPiece` aggregates selected outputs from upstream pieces into one JSON file: `dashboard_data.json`.
That JSON is then consumed by `app.py` (Streamlit dashboard).

## Expected Inputs
Inputs are defined in `models.py` / `metadata.json`.

1. `preprocess_predict_parquet`
- Expected file: `predict_dataset_15min.parquet`
- Source: `PreprocessEnergyDataPiece`
- Note: `train_dataset.parquet` is intentionally ignored.

2. `predict_predictions_csv`
- Expected file: `predictions_15min.csv`
- Source: `PredictPiece`
- Note: `prediction_log.txt` is intentionally ignored.

3. `simulate_results_csv`
- Expected file: `simulated_results.csv`
- Source: `SimulatePiece`

4. `simulate_summary_csv`
- Expected file: `summary.csv`
- Source: `SimulatePiece`

5. `kpi_results_csv`
- Expected file: `kpi_results.csv`
- Source: `KPIPiece`

6. `investment_evaluation_csv`
- Expected file: `investment_evaluation.csv`
- Source: `InvestmentEvalPiece`

7. `dashboard_data_json`
- Output file path to write consolidated dashboard data.

## Output
`dashboard_data_json` (JSON file) with this high-level structure:

- `meta`
- `inputs` (per-input status, rows, errors)
- `scenarios`
- `default_scenario`
- `datasets`

`datasets` includes:
- `preprocess_predict`
- `predict_predictions`
- `simulate_results`
- `simulate_summary`
- `kpi_results`
- `investment_evaluation`

## Core Logic (`piece.py`)
1. Iterate over a central `FILE_SPECS` mapping.
2. Read each file safely (`csv` or `parquet`).
3. Convert tables to JSON-safe row records.
4. Record input status (provided/missing/error/row count).
5. Extract scenario options from scenario-like columns.
6. Write all results into `dashboard_data.json`.

If a file is missing or invalid, no exception is raised for the full piece run. That dataset is stored as empty and the error is reported in `inputs`.

## Run DashboardPiece with Actual TEST Files
From repository root:

```bash
cd <path_to_repository_root>

/usr/local/bin/python3 - <<'PY'
from domino.testing.dry_run import piece_dry_run

piece_dry_run(
    repository_folder_path='.',
    piece_name='DashboardPiece',
    input_data={
        'preprocess_predict_parquet': '<path_to_input_file>',
        'predict_predictions_csv': '<path_to_input_file>',
        'simulate_results_csv': '<path_to_input_file>',
        'simulate_summary_csv': '<path_to_input_file>',
        'kpi_results_csv': '<path_to_input_file>',
        'investment_evaluation_csv': '<path_to_input_file>',
        'dashboard_data_json': '<path_to_output_file>',
    },
)
print('Wrote <path_to_output>/dashboard_data.json')
PY
```

## Feed Output into Streamlit and Launch
`app.py` reads `dashboard_data.json` from the current working directory. Easiest path:

```bash
cd <path_to_dashboard_piece_dir>
/usr/local/bin/python3 -m streamlit run app.py
```

Open the URL shown in terminal (usually `http://localhost:8501`).

## Tests
```bash
cd <path_to_repository_root>
/usr/local/bin/python3 -m pytest pieces/DashboardPiece/test_DashboardPiece.py -q
```
