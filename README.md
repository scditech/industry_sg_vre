# Industry Smart Grid Virtual RE Pilot Project – Domino Pieces Repository

**Owner:** scditech (SCDI)  
**Project:** Industry Smart Grid Virtual RE

## Structure

- `pieces/`: Domino Pieces
- `dependencies/`: Docker and requirements files
- `config.toml`: Repository configuration
- `.github/workflows/`: CI/CD for building Pieces

## Usage

1. Install Domino CLI
2. Run: `domino-pieces publish`

## Pieces Overview

| Piece | Purpose |
|-------|---------|
| FetchEnergyDataPiece | Merge load, production, and price CSVs into one Parquet dataset. |
| PreprocessEnergyDataPiece | Build training and prediction datasets (15‑min, time/lag features). |
| TrainModelPiece | Train XGBoost model to forecast load (load_kw). |
| PredictPiece | Generate 15‑min load forecasts (predictions_15min.csv). |
| SolarSimPiece | Simulate PV output (virtual_solar.csv) from weather and solar_config.yml. |
| BatterySimPiece | Simulate battery charge/discharge and grid import (virtual_battery_soc.csv, battery_summary.csv). |
| SimulatePiece | Compute baseline vs. scenario costs (simulated_results.csv, summary.csv). |
| KPIPiece | Compute KPIs: kWh/ton, peak reduction, savings, CO₂ (kpi_results.csv). |
| InvestmentEvalPiece | Investment evaluation: CAPEX, payback, NPV, LCOE (investment_evaluation.csv). |
| DashboardPiece | Aggregate piece outputs into dashboard_data.json for the Streamlit dashboard. |
