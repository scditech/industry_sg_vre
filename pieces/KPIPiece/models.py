from pydantic import BaseModel, Field


class InputModel(BaseModel):
    forecast_csv: str = Field(description="Path to predictions_15min.csv")
    simulated_load_csv: str = Field(description="Path to simulated_results.csv")
    scenario_summary_csv: str = Field(description="Path to summary.csv from SimulatePiece")
    production_csv: str = Field(description="Production tons csv from disk")
    actual_csv: str = Field(default="", description="Optional actual load csv")


class OutputModel(BaseModel):
    message: str
    kpi_results_csv: str
