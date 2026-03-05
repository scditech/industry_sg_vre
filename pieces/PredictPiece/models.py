from pydantic import BaseModel, Field


class InputModel(BaseModel):
    model_path: str = Field(description="Path to trained XGBoost model")
    data_path: str = Field(description="Path to prediction dataset (15min)")


class OutputModel(BaseModel):
    message: str
    prediction_file_path: str
