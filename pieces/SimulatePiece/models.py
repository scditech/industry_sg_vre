
from pydantic import BaseModel, Field


class InputModel(BaseModel):
    forecast_csv: str = Field(description="Path to predictions_15min.csv from PredictPiece")
    virtual_solar_csv: str = Field(description="Path to virtual_solar.csv", default="")
    virtual_battery_soc_csv: str = Field(description="Path to virtual_battery_soc.csv", default="")
    scenario_yml: str = Field(description="Path to scenario yaml file")


class OutputModel(BaseModel):
    message: str
    simulated_load_csv: str
    scenario_summary_csv: str
