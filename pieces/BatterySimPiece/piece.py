from pathlib import Path

from domino.base_piece import BasePiece
from .models import InputModel, OutputModel
import pandas as pd
import yaml


class BatteryModel:
    def __init__(self, capacity_kwh: float, charge_eff: float, discharge_eff: float,
                 max_c_rate: float, strategy: dict):
        self.capacity = capacity_kwh
        self.charge_eff = charge_eff
        self.discharge_eff = discharge_eff
        self.max_power = max_c_rate * capacity_kwh  # kW
        self.strategy = strategy  # dict with peak_hours, charge_from, etc.

    def simulate(self, solar_power_df: pd.DataFrame, load_forecast_df: pd.DataFrame = None) -> tuple[pd.Series, pd.Series]:
        """
        Expects:
          - solar_power_df: columns ['datetime','solar_kw']
          - load_forecast_df: optional, columns 'prediction_load_mw' or 'prediction_load_kw'
        Returns (soc_series, grid_import_series) indexed by datetime.
        """
        # Prepare merged dataframe with solar_kw and load_kw (kW)
        solar = solar_power_df.copy()
        if load_forecast_df is not None:
            lf = load_forecast_df.copy()
            # len predpoveď zaťaženia (prediction_*); load_kw/load_mw sú skutočné odbery, nie forecast
            if "prediction_load_mw" in lf.columns:
                lf["load_kw"] = lf["prediction_load_mw"] * 1000.0
            elif "prediction_load_kw" in lf.columns:
                lf["load_kw"] = lf["prediction_load_kw"]
            else:
                lf["load_kw"] = 0.0
            # Podpora oboch formátov: Solargis :07/:22/:37/:52 aj štandard :00/:15/:30/:45 – zjednotenie cez floor 15 min
            solar_ts = pd.to_datetime(solar["datetime"])
            lf_ts = pd.to_datetime(lf["datetime"])
            solar["_t_15"] = solar_ts.dt.floor("15min")
            lf["_t_15"] = lf_ts.dt.floor("15min")
            lf_sel = lf[["_t_15", "load_kw"]].drop_duplicates(subset=["_t_15"], keep="first")
            merged = solar.merge(lf_sel, on="_t_15", how="left", suffixes=("", "_lf"))
            merged = merged.drop(columns=["_t_15"], errors="ignore")
            merged["load_kw"] = merged["load_kw"].fillna(0.0)
            if merged["load_kw"].eq(0.0).all() and len(lf) > 0:
                import warnings as _w
                _w.warn(
                    "BatterySim: forecast a solar nemajú prekrývajúce sa dátumy/časy – load_kw bude 0. "
                    "Daj predictions v rovnakom období ako virtual_solar (rovnaké dni).",
                    UserWarning,
                    stacklevel=1,
                )
        else:
            merged = solar.copy()
            merged["load_kw"] = 0.0

        # compute net load in kW: positive => import (load > solar), negative => export / excess
        merged["net_kw"] = merged["load_kw"] - merged.get("solar_kw", 0.0)

        # infer timestep in hours (e.g. 0.25 for 15 min)
        if "datetime" in merged.columns and len(merged) >= 2:
            diffs = pd.to_datetime(merged["datetime"]).diff().dropna()
            dt_h = diffs.iloc[0].total_seconds() / 3600.0 if len(diffs) > 0 else 0.25
        else:
            dt_h = 0.25

        soc = [self.strategy.get("initial_soc", 50.0)]
        grid = []

        # helper to parse peak hour values
        def _parse_hour(v):
            if isinstance(v, str):
                return int(v.split(":")[0])
            return int(v)

        peak = self.strategy.get("peak_hours")
        if peak and isinstance(peak.get("start"), (str, int)):
            try:
                peak = {"start": _parse_hour(peak["start"]), "end": _parse_hour(peak["end"])}
            except Exception:
                peak = None

        for _, row in merged.iterrows():
            net = float(row["net_kw"])  # kW
            # hour for peak detection
            hour = row["datetime"].hour if "datetime" in merged.columns else getattr(row, "Index", None)
            in_peak = False
            if peak:
                in_peak = peak["start"] <= hour < peak["end"]

            # Discharge during peak to reduce imports (net > 0 means import)
            # deliver_kw = power to grid; from battery we take deliver_kw*dt/discharge_eff (kWh)
            if in_peak and soc[-1] > 10 and net > 0:
                available_kwh = (soc[-1] / 100.0) * self.capacity
                # max energy deliverable to grid = available_kwh * discharge_eff
                max_deliver_kw = min(net, self.max_power, available_kwh * self.discharge_eff / dt_h)
                deliver_kw = max_deliver_kw
                grid.append(net - deliver_kw)
                # SOC decrease: energy taken from battery = deliver_kw * dt / discharge_eff
                delta_soc = (deliver_kw * dt_h / self.discharge_eff / self.capacity) * 100.0
                new_soc = soc[-1] - delta_soc
            # Charge from solar excess (kedykoľvek net < 0), aby sa batéria dobil cez deň a predpoveď bola verná
            # energy stored = charge_kw * dt * charge_eff
            elif soc[-1] < 90 and net < 0:
                excess = -net
                max_charge_power = (90.0 - soc[-1]) / 100.0 * self.capacity / dt_h
                charge_kw = min(self.max_power, excess, max_charge_power)
                grid.append(net + charge_kw)
                delta_soc = (charge_kw * dt_h * self.charge_eff / self.capacity) * 100.0
                new_soc = soc[-1] + delta_soc
            else:
                grid.append(net)
                new_soc = soc[-1]

            soc.append(max(0.0, min(100.0, new_soc)))

        # create series indexed by datetime if present
        index = merged["datetime"] if "datetime" in merged.columns else merged.index
        soc_series = pd.Series(soc[1:], index=index, name="soc_pct")
        grid_series = pd.Series(grid, index=index, name="grid_import_kw")
        return soc_series, grid_series


class BatterySimPiece(BasePiece):

    def piece_function(self, input_data: InputModel) -> OutputModel:
        # solar generation input (kW)
        df_solar_power = pd.read_csv(input_data.input_load_data, parse_dates=["datetime"])
        # load forecast input (MW) — predictions_15min.csv: 'prediction_load_mw'
        df_load_forecast = None
        try:
            df_load_forecast = pd.read_csv(input_data.input_forecast, parse_dates=["datetime"])
        except Exception:
            df_load_forecast = None

        with open(input_data.input_Battery_config) as f:
            battery_config = yaml.safe_load(f) or {}
        with open(input_data.input_scenario) as f:
            scenario = yaml.safe_load(f) or {}

        # Build/normalize strategy: prefer scenario.strategy, fallback to time_window.peak_hours
        strategy = (scenario.get("strategy") or {}).copy()
        if "peak_hours" not in strategy:
            tw = scenario.get("time_window") or {}
            if isinstance(tw, dict) and "peak_hours" in tw:
                strategy["peak_hours"] = tw["peak_hours"]

        # default initial SOC from battery config if present
        if "initial_soc" not in strategy:
            strategy["initial_soc"] = battery_config.get("initial_soc", battery_config.get("initial_soc_pct", 50))

        model = BatteryModel(
            capacity_kwh=battery_config.get("capacity_kWh"),
            charge_eff=battery_config.get("charge_efficiency"),
            discharge_eff=battery_config.get("discharge_efficiency"),
            max_c_rate=battery_config.get("max_c_rate"),
            strategy=strategy,
        )

        soc, grid = model.simulate(df_solar_power, df_load_forecast)

        # SOC + grid_import_kw (pre SimulatePiece – detailný výstup batérie)
        out_df = pd.DataFrame({
            "soc_pct": soc.values,
            "grid_import_kw": grid.values,
        }, index=soc.index)
        out_df.index.name = "datetime"
        out_df.to_csv(
            input_data.output_path,
            date_format="%Y-%m-%d %H:%M:%S",
        )

        # compute some summary KPIs: 1 full cycle = 200% SOC change (0→100→0)
        capacity = battery_config.get("capacity_kWh")
        soc_changes_pct = soc.diff().abs().sum()
        cycles_equivalent = soc_changes_pct / 200.0 if soc_changes_pct > 0 else 0.0
        energy_throughput = (soc_changes_pct / 100.0) * capacity / 1000.0 if capacity else None

        summary = {
            "capacity_kWh": capacity,
            "cycles_equivalent": cycles_equivalent,
            "energy_throughput_MWh": energy_throughput,
        }

        # CSV súhrn pre InvestmentEvalPiece (očakáva stĺpec cycles_equivalent)
        summary_path = str(Path(input_data.output_path).parent / "battery_summary.csv")
        pd.DataFrame([summary]).to_csv(summary_path, index=False)

        summary_str = "\n".join(f"{k}: {v}" for k, v in summary.items())
        if getattr(self, "logger", None) is not None:
            self.logger.info("Battery simulation finished:\n%s", summary_str)
        print(f"[INFO] Battery simulation finished, saved to {input_data.output_path}")
        print(f"[INFO] Battery summary (cycles, throughput) saved to {summary_path}")

        return OutputModel(
            output_path=input_data.output_path,
            summary_csv_path=summary_path,
            summary=summary_str,
        )