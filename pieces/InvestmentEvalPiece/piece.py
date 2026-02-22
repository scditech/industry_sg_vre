from domino.base_piece import BasePiece
from .models import InputModel, OutputModel

from pathlib import Path
import pandas as pd
import yaml

from .models import simple_payback, npv, co2_saved, lcoe


class InvestmentEvalPiece(BasePiece):

    def piece_function(self, input_data: InputModel) -> OutputModel:

        print("\n[INFO] ===== INVESTMENT PIECE START =====")

        kpi_csv = Path(input_data.kpi_results_csv)
        bat_csv = Path(input_data.battery_summary_csv)
        cfg_yml = Path(input_data.investment_config_yml)

        if not kpi_csv.exists():
            raise FileNotFoundError(f"KPI csv not found: {kpi_csv}")

        if not bat_csv.exists():
            raise FileNotFoundError(f"Battery summary not found: {bat_csv}")

        if not cfg_yml.exists():
            raise FileNotFoundError(f"Config yaml not found: {cfg_yml}")

        print("[INFO] Loading KPI & config")

        # ✅ správne čítanie KPI (1 riadok dataframe)
        kpi_df = pd.read_csv(kpi_csv)
        bat_df = pd.read_csv(bat_csv)

        with open(cfg_yml) as f:
            cfg = yaml.safe_load(f)

        # -----------------------------
        # CAPEX
        # -----------------------------
        solar_capex = cfg["solar_capex_eur"]
        battery_capex = cfg["battery_capex_eur"]
        total_capex = solar_capex + battery_capex

        annual_savings = float(kpi_df["annual_savings_eur"].iloc[0])
        annual_pv_mwh = float(kpi_df.get("annual_pv_mwh_est", pd.Series([0])).iloc[0])

        degradation = cfg.get("degradation_per_year", 0.005)
        discount = cfg.get("discount_rate", 0.08)
        years = cfg.get("analysis_years", 15)

        print(f"[DEBUG] CAPEX total: {total_capex:,.0f} €")
        print(f"[DEBUG] Annual savings: {annual_savings:,.0f} €")

        # -----------------------------
        # FINANCE
        # -----------------------------
        payback_val = simple_payback(total_capex, annual_savings)
        npv_val = npv(total_capex, annual_savings, years, discount)
        co2_val = co2_saved(annual_pv_mwh)
        lcoe_val = lcoe(solar_capex, annual_pv_mwh, degradation, years)

        battery_cycles = 0
        if "cycles_equivalent" in bat_df.columns:
            battery_cycles = float(bat_df["cycles_equivalent"].iloc[0])

        eval_dict = {
            "total_capex_eur": total_capex,
            "solar_capex_eur": solar_capex,
            "battery_capex_eur": battery_capex,
            "annual_savings_eur": annual_savings,
            "simple_payback_years": payback_val,
            "npv_eur": npv_val,
            "solar_lcoe_eur_per_mwh": lcoe_val,
            "annual_co2_saved_ton": co2_val,
            "battery_cycles_est": battery_cycles
        }

        out_path = Path(self.results_path) / "investment_eval.csv"
        pd.DataFrame([eval_dict]).to_csv(out_path, index=False)

        print("\n[SUCCESS] INVESTMENT EVALUATION COMPLETE")
        print(eval_dict)

        return OutputModel(
            message="Investment evaluation finished",
            investment_evaluation_json=str(out_path)
        )
