from pydantic import BaseModel, Field


class InputModel(BaseModel):
    kpi_results_csv: str = Field(description="From KPIPiece")
    battery_summary_csv: str = Field(default="/home/shared_storage/battery_summary_TEST.csv", description="Battery summary csv")
    investment_config_yml: str = Field(default="/home/shared_storage/investment_config.yml", description="Investment config yaml")


class OutputModel(BaseModel):
    message: str
    investment_evaluation_json: str
