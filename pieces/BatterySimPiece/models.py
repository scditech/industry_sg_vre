from pydantic import BaseModel, Field


class InputModel(BaseModel):
    """
    BatterySimPiece Input Model
    """
    input_load_data: str = Field(
        title="Path to virtual solar energy generation CSV",
        default="virtual_solar.csv",
        description="CSV file containing virtual solar generation data with columns: datetime, solar_kw)",
    )

    input_Battery_config: str = Field(
        title="Path to battery configuration file battery_config.yml",
        default="battery_config.yml",
        description="YAML file containing configuration for battery simulation.",
    )

    input_forecast: str = Field(
        title="Path to net load forecast CSV",
        default="forecast.csv",
        description="CSV file containing net load forecast data with columns: datetime, load_mw, production_ton, price_eur_mwh, prediction_load_mw",
    )

    input_scenario: str = Field(
        title="Path to battery scenario configuration file scenario.yml",
        default="scenario.yml",
        description="YAML file containing scenario configuration with battery operation strategy.",
    )

    output_path: str = Field(
        title="Battery simulation CSV output path",
        default="virtual_battery_soc.csv",
        description="Path to generated battery simulation data CSV file.",
    )

class OutputModel(BaseModel):
    """
    BatterySimPiece Output Model
    """
    output_path: str = Field(
        title="Path to SOC CSV",
        description="Path to the generated virtual_battery_soc.csv file.",
        default="",
    )
    summary_csv_path: str = Field(
        title="Path to battery summary CSV",
        description="Path to battery_summary.csv (capacity_kWh, cycles_equivalent, energy_throughput_MWh) for InvestmentEvalPiece.",
        default="",
    )
    summary: str = Field(
        title="Results summary",
        description="Summary of battery simulation results (text).",
    )