from domino.base_piece import BasePiece
from .models import InputModel, OutputModel

import pandas as pd
from pathlib import Path


class KPIPiece(BasePiece):

    def piece_function(self, input_data: InputModel) -> OutputModel:

        print("\n[INFO] ===== KPI PIECE START =====")

        forecast_csv = Path(input_data.forecast_csv)
        sim_csv = Path(input_data.simulated_load_csv)
        scen_csv = Path(input_data.scenario_summary_csv)
        prod_csv = Path(input_data.production_csv)
        actual_csv = Path(input_data.actual_csv) if input_data.actual_csv else None

        if not forecast_csv.exists():
            raise FileNotFoundError(f"Forecast CSV not found: {forecast_csv}")
        if not sim_csv.exists():
            raise FileNotFoundError(f"Simulated CSV not found: {sim_csv}")
        if not scen_csv.exists():
            raise FileNotFoundError(f"Scenario summary not found: {scen_csv}")
        if not prod_csv.exists():
            raise FileNotFoundError(f"Production CSV not found: {prod_csv}")

        print("[INFO] Loading CSVs")

        fc = pd.read_csv(forecast_csv, parse_dates=["datetime"])
        sim = pd.read_csv(sim_csv, parse_dates=["datetime"])
        prod = pd.read_csv(prod_csv, parse_dates=["datetime"])
        scen = pd.read_csv(scen_csv)

        # =========================================================
        # ENERGY PER TON
        # =========================================================
        print("[INFO] Calculating kWh per ton")

        sim["energy_kwh"] = sim["simulated_load_kw"] * 0.25
        sim_daily = sim.set_index("datetime").resample("D")["energy_kwh"].sum()

        prod_daily = prod.set_index("datetime").resample("D")["production_ton"].sum()

        merged = pd.concat([sim_daily, prod_daily], axis=1).dropna()

        if len(merged) == 0:
            kwh_per_ton = 0.0
        else:
            total_energy_kwh = merged["energy_kwh"].sum()
            total_production_ton = merged["production_ton"].sum()
            if total_production_ton > 0:
                kwh_per_ton = total_energy_kwh / total_production_ton
            else:
                kwh_per_ton = 0.0

        # =========================================================
        # PEAKS
        # =========================================================
        baseline_peak = sim["baseline_load_kw"].max()
        simulated_peak = sim["simulated_load_kw"].max()
        peak_reduction = baseline_peak - simulated_peak

        # =========================================================
        # MONEY
        # =========================================================
        baseline_cost = float(scen["baseline_cost_eur"].iloc[0])
        scenario_cost = float(scen["scenario_cost_eur"].iloc[0])
        savings = float(scen["savings_eur"].iloc[0])

        days = float(scen["days_simulated"].iloc[0])
        yearly_savings = savings * (365 / days) if days > 0 else 0

        # =========================================================
        # PV MWh estimate (rough from difference)
        # =========================================================
        energy_diff = (sim["baseline_load_kw"] - sim["simulated_load_kw"]).clip(lower=0)
        pv_mwh = (energy_diff.sum() * 0.25) / 1000

        co2_saved = pv_mwh * 0.57

        # =========================================================
        # FORECAST MAPE (optional)
        # =========================================================
        mape_val = None
        if actual_csv and actual_csv.exists():
            print("[INFO] Calculating MAPE")
            act = pd.read_csv(actual_csv, parse_dates=["datetime"])

            merged_fc = pd.merge(
                fc[["datetime", "prediction_load_kw"]],
                act[["datetime", "load_kw"]],
                on="datetime",
                how="inner"
            )

            if len(merged_fc) > 0:
                mape_val = (
                    (merged_fc["prediction_load_kw"] - merged_fc["load_kw"]).abs()
                    / merged_fc["load_kw"]
                ).mean() * 100

        # =========================================================
        # SAVE KPI
        # =========================================================
        kpi_dict = {
            "kwh_per_ton": kwh_per_ton,
            "baseline_peak_kw": baseline_peak,
            "simulated_peak_kw": simulated_peak,
            "peak_reduction_kw": peak_reduction,
            "annual_savings_eur": yearly_savings,
            "period_savings_eur": savings,
            "annual_pv_mwh_est": pv_mwh * (365 / days) if days > 0 else 0,
            "co2_saved_ton_est": co2_saved * (365 / days) if days > 0 else 0,
            "forecast_mape_pct": mape_val
        }

        kpi_df = pd.DataFrame([kpi_dict])

        out_path = Path(self.results_path) / "kpi_results.csv"
        kpi_df.to_csv(out_path, index=False)

        print("\n[SUCCESS] KPI computed")
        print(kpi_dict)

        return OutputModel(
            message="KPI calculation finished",
            kpi_results_csv=str(out_path)
        )
