from pydantic import BaseModel, Field


class InputModel(BaseModel):
    """
    SolarSimPiece Input Model
    """
    input_weather_data: str = Field(
        title="Path to weather data CSV",
        default="weather.csv",
        description="CSV file containing weather data with columns: datetime, ghi, dni, dhi, temp_air, wind_speed)",
    )

    input_Virtual_RE_config: str = Field(
        title="Path to virtual RE configuration file solar_config.yml",
        default="solar_config.yml",
        description="YAML file containing configuration for virtual solar generation.",
    )

    output_path: str = Field(
        title="Virtual solar CSV output path",
        default="virtual_solar.csv",
        description="Path to generated virtual solar data CSV file.",
    )


class OutputModel(BaseModel):
    """
    SolarSimPiece Output Model
    """
    output_path: str = Field(
        title="Virtual solar CSV output path",
        description="Path to generated virtual solar data CSV file.",
    )