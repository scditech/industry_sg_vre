from pydantic import BaseModel, Field


class InputModel(BaseModel):
    input_path: str = Field(
        description="Path to merged energy parquet file"
    )

    forecast_hours: int = Field(
        default=24,
        description="Forecast horizon in hours"
    )


class OutputModel(BaseModel):
    message: str
    train_file_path: str
    predict_file_path: str
