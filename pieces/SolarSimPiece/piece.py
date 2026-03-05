from domino.base_piece import BasePiece
from .models import InputModel, OutputModel
import pandas as pd
import yaml
from pvlib import location, pvsystem, modelchain, temperature


class SolarSimPiece(BasePiece):
    
    def piece_function(self, input_data: InputModel):
    
        print(f"[INFO] Reading weather data from {input_data.input_weather_data}")
        # Prefer Solargis preprocessing, but gracefully fall back to plain CSV
        # with columns: datetime, ghi, dni, dhi, temp_air, wind_speed.
        df_weather = preprocess_solargis(input_data.input_weather_data)
        if df_weather is None or df_weather.empty or len(df_weather.columns) == 0:
            df_weather = pd.read_csv(
                input_data.input_weather_data,
                parse_dates=["datetime"],
                index_col="datetime",
            )

        print(f"[INFO] Reading solar config from {input_data.input_Virtual_RE_config}")
        with open(input_data.input_Virtual_RE_config, "r") as f:
            cfg = yaml.safe_load(f)

        solar_kw = get_solar_profile(df_weather, cfg)
        solar_kw = solar_kw.clip(lower=0.0)
        solar_kw.name = "solar_kw"
        solar_kw.to_frame().to_csv(
            input_data.output_path,
            index_label="datetime",
            date_format="%Y-%m-%d %H:%M:%S",
        )
        print(f"[INFO] Virtual solar profile saved to {input_data.output_path}")
        return OutputModel(output_path=input_data.output_path)


def get_solar_profile(df_weather: pd.DataFrame, cfg: dict) -> pd.Series:
    """
    pvlib-based model: používa SAM modul a menič, dimenzuje počet modulov podľa capacity_kWp
    a vracia AC výkon v kW pre celý systém.
    """
    loc = location.Location(
        latitude=cfg["site_latitude"],
        longitude=cfg["site_longitude"],
        altitude=cfg["site_altitude"],
    )
    sandia_modules = pvsystem.retrieve_sam("SandiaMod")
    sapm_inverters = pvsystem.retrieve_sam("CECInverter")
    module_name = cfg.get("module_name", "Canadian_Solar_CS6X_300M__2013_")
    inverter_name = cfg.get("inverter_name", "ABB__MICRO_0_25_I_OUTD_US_208__208V_")
    module = sandia_modules[module_name]
    inverter = sapm_inverters[inverter_name]
    temp_model_params = temperature.TEMPERATURE_MODEL_PARAMETERS["sapm"]["open_rack_glass_glass"]

    # Modelujeme 1 menič + jeho priradené moduly a následne škálujeme
    # výsledok podľa požadovaného AC výkonu elektrárne.
    inverter_power_w = float(inverter.get("Paco", inverter.get("Pdco")))
    plant_power_w = float(cfg["capacity_kWp"]) * 1000.0
    num_inverters = plant_power_w / inverter_power_w if inverter_power_w > 0 else 1.0

    modules_per_string = 1
    strings_per_inverter = 1

    mc = modelchain.ModelChain(
        system=pvsystem.PVSystem(
            surface_tilt=cfg["tilt"],
            surface_azimuth=cfg["azimuth"],
            module_parameters=module,
            inverter_parameters=inverter,
            modules_per_string=modules_per_string,
            strings_per_inverter=strings_per_inverter,
            temperature_model_parameters=temp_model_params,
        ),
        location=loc,
        name="ISGvRE_Virtual_PV",
    )

    mc.run_model(df_weather)

    ac = mc.results.ac
    if isinstance(ac, pd.DataFrame):
        if ac.shape[1] == 1:
            per_inverter_ac_w = ac.iloc[:, 0]
        else:
            per_inverter_ac_w = ac.sum(axis=1)
    else:
        per_inverter_ac_w = ac

    system_ac_w = per_inverter_ac_w * num_inverters
    derate = float(cfg.get("efficiency", 1.0))
    solar_kw = (system_ac_w / 1000.0 * derate).astype(float).fillna(0.0).clip(lower=0.0)
    solar_kw.name = "solar_kw"
    return solar_kw


def preprocess_solargis(solgis_path: str) -> pd.DataFrame:
    """
    Read a SolarGIS ';' file and return a DataFrame with index datetime and
    columns: ghi, dni, dhi, temp_air, wind_speed (matching existing piece expectations).
    - Ignores lines starting with '#'
    - Combines 'Date' and 'Time' into a single datetime (dayfirst=True for DD.MM.YYYY)
    - Renames DIF -> dhi, TEMP -> temp_air, WS -> wind_speed
    - Replaces -9 (no-data) with NaN and coerces numeric types
    """
    df = pd.read_csv(solgis_path, sep=";", comment="#", engine="python")
    # combine date+time to datetime (SolarGIS uses DD.MM.YYYY)
    if "Date" in df.columns and "Time" in df.columns:
        df["datetime"] = pd.to_datetime(
            df["Date"].astype(str).str.strip() + " " + df["Time"].astype(str).str.strip(),
            dayfirst=True,
            errors="coerce",
        )
        df = df.drop(columns=[c for c in ("Date", "Time") if c in df.columns])
    elif "Date" in df.columns:
        df["datetime"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
    # standardize column names (case-insensitive)
    col_map = {}
    cols_lower = {c.lower(): c for c in df.columns}
    if "ghi" in cols_lower:
        col_map[cols_lower["ghi"]] = "ghi"
    if "dni" in cols_lower:
        col_map[cols_lower["dni"]] = "dni"
    # SolarGIS uses DIF -> diffuse horizontal irradiance
    if "dif" in cols_lower:
        col_map[cols_lower["dif"]] = "dhi"
    if "dhi" in cols_lower:
        col_map[cols_lower["dhi"]] = "dhi"
    if "temp" in cols_lower:
        col_map[cols_lower["temp"]] = "temp_air"
    if "temp" not in cols_lower and "temp" not in col_map and "temp" in df.columns:
        col_map["temp"] = "temp_air"
    if "ws" in cols_lower:
        col_map[cols_lower["ws"]] = "wind_speed"
    if "wind_speed" in cols_lower:
        col_map[cols_lower["wind_speed"]] = "wind_speed"
    df = df.rename(columns=col_map)
    # Coerce numeric columns and handle no-data marker (-9)
    for c in ("ghi", "dni", "dhi", "temp_air", "wind_speed"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
            df.loc[df[c] == -9, c] = pd.NA
    # ensure datetime index
    if "datetime" in df.columns:
        df = df.set_index("datetime")
    df = df.sort_index()
    # Keep only the expected columns if present
    expected = [c for c in ("ghi", "dni", "dhi", "temp_air", "wind_speed") if c in df.columns]
    return df[expected]

# ----------------------------------------------------------------------------------
# --------------------------------- Reference --------------------------------------
# ----------------------------------------------------------------------------------
# def get_solar_profile(df_weather: pd.DataFrame, cfg: dict) -> pd.Series:
#     """
#     Returns 15-min solar generation (kW) based on weather CSV.
#     df_weather must contain columns: datetime, ghi, dni, dhi, temp_air, wind_speed
#     """
#     loc = location.Location(
#         latitude=cfg["site_latitude"],
#         longitude=cfg["site_longitude"],
#         altitude=cfg["site_altitude"],
#     )
#     # build PV module & inverter from database
#     sandia_modules = pvsystem.retrieve_sam("SandiaMod")
#     sapm_inverters = pvsystem.retrieve_sam("cecinverter")
#     module = sandia_modules["Canadian_Solar_CS6X_300M__2013_"]
#     inverter = sapm_inverters["ABB__MICRO_0_25_I_OUTD_US_208_208_60_"]
#     temp_model_params = temperature.TEMPERATURE_MODEL_PARAMETERS["sapm"]["open_rack_glass_glass"]
#     # sizing
#     modules_per_string = int(cfg["capacity_kWp"] * 1000 / module.STC)
#     strings = 1
#     # model chain
#     mc = modelchain.ModelChain(
#         system=pvsystem.PVSystem(
#             surface_tilt=cfg["tilt"],
#             surface_azimuth=cfg["azimuth"],
#             module_parameters=module,
#             inverter_parameters=inverter,
#             modules_per_string=modules_per_string,
#             strings_per_inverter=strings,
#             temperature_model_parameters=temp_model_params,
#         ),
#         location=loc,
#         orientation_strategy=None,
#         name="Chemosvit_Virtual_PV",
#     )
#     # run model
#     mc.run_model(df_weather)
#     # return kW
#     return mc.results.ac / 1000.0  # W → kW


# def __init__(self, *args, **kwargs):
#     super().__init__(*args, **kwargs)
#     self.weather_csv = self.inputs["weather_csv"]
#     self.solar_config_yml = self.inputs["solar_config_yml"]
#     self.out_file = self.outputs["virtual_solar_csv"]


# def run(self):
#     df_weather = pd.read_csv(self.weather_csv, parse_dates=["datetime"])
#     with open(self.solar_config_yml, "r") as f:
#         cfg = yaml.safe_load(f)
#     solar_kw = get_solar_profile(df_weather, cfg)
#     solar_kw.to_csv(self.out_file, header=True, index_label="datetime")
#     self.logger.info("Virtual solar profile saved to %s", self.out_file)