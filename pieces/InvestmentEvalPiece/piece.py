from domino.base_piece import BasePiece
from .models import InputModel, OutputModel

from pathlib import Path
import pandas as pd
import yaml


# ===============================
# FINANCIAL FUNCTIONS
# ===============================

def simple_payback(capex: float, annual_savings: float) -> float:
    return capex / annual_savings if annual_savings > 0 else 999


def npv(capex: float, annual_cash: float, years: int, dr: float) -> float:
    factor = (1 - (1 + dr) ** -years) / dr
    return -capex + annual_cash * factor


def co2_saved(annual_pv_mwh: float, grid_factor: float = 0.57) -> float:
    return annual_pv_mwh * grid_factor


def lcoe(capex: float, annual_mwh: float, degradation: float, years: int) -> float:
    total_mwh = sum(annual_mwh * (1 - degradation) ** y for y in range(years))
    return capex / total_mwh if total_mwh > 0 else 999


# ===============================
# PIECE
# ===============================

class InvestmentEvalPiece(BasePiece):

    def piece_function(self, input_data: InputModel) -> OutputModel:

        print("\n[INFO] ===== INVESTMENT PIECE START =====")

        kpi_csv = Path(input_data.kpi_results_csv)
        battery_csv = Path(input_data.battery_summary_csv)
        config_yml = Path(input_data.investment_config_yml)

        # ---------------------------
        # VALIDATION
        # ---------------------------
        if not kpi_csv.exists():
            raise FileNotFoundError(f"KPI CSV not found: {kpi_csv}")

        if not battery_csv.exists():
            raise FileNotFoundError(f"Battery summary CSV not found: {battery_csv}")

        if not config_yml.exists():
            raise FileNotFoundError(f"Investment config YAML not found: {config_yml}")

        print("[INFO] Loading inputs")

        kpi_df = pd.read_csv(kpi_csv)
        battery_df = pd.read_csv(battery_csv)

        with open(config_yml) as f:
            cfg = yaml.safe_load(f)

        # ---------------------------
        # EXTRACT VALUES
        # ---------------------------
        annual_savings = float(kpi_df["annual_savings_eur"].iloc[0])
        annual_pv_mwh = float(kpi_df.get("annual_pv_mwh_est", pd.Series([0])).iloc[0])

        solar_capex = float(cfg["solar_capex_eur"])
        battery_capex = float(cfg["battery_capex_eur"])
        total_capex = solar_capex + battery_capex

        degradation = cfg.get("degradation_per_year", 0.005)
        discount_rate = cfg.get("discount_rate", 0.08)
        years = cfg.get("analysis_years", 15)

        battery_cycles = 0
        if "cycles_equivalent" in battery_df.columns:
            battery_cycles = float(battery_df["cycles_equivalent"].iloc[0])

        print(f"[DEBUG] Total CAPEX: {total_capex:,.0f} €")
        print(f"[DEBUG] Annual savings: {annual_savings:,.0f} €")

        # ---------------------------
        # CALCULATIONS
        # ---------------------------
        payback_years = simple_payback(total_capex, annual_savings)
        npv_value = npv(total_capex, annual_savings, years, discount_rate)
        lcoe_value = lcoe(solar_capex, annual_pv_mwh, degradation, years)
        co2_value = co2_saved(annual_pv_mwh)

        # ---------------------------
        # SAVE OUTPUT
        # ---------------------------
        result_dict = {
            "total_capex_eur": total_capex,
            "solar_capex_eur": solar_capex,
            "battery_capex_eur": battery_capex,
            "annual_savings_eur": annual_savings,
            "simple_payback_years": payback_years,
            "npv_eur": npv_value,
            "solar_lcoe_eur_per_mwh": lcoe_value,
            "annual_co2_saved_ton": co2_value,
            "battery_cycles_est": battery_cycles
        }

        out_path = Path(self.results_path) / "investment_evaluation.csv"
        pd.DataFrame([result_dict]).to_csv(out_path, index=False)

        print("\n[SUCCESS] ===== INVESTMENT COMPLETE =====")
        print(result_dict)

        return OutputModel(
            message="Investment evaluation finished",
            investment_evaluation_json=str(out_path)
        )
