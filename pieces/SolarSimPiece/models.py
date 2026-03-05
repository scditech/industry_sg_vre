from pydantic import BaseModel, Field


class InputModel(BaseModel):
    """
    SolarSimPiece Input Model
    """
    input_weather_data: str = Field(
        title="Path to weather data CSV",
        default="/home/shared_storage/SolarGIS.csv",
        description="CSV file containing weather data (Solargis or columns: datetime, ghi, dni, dhi, temp_air, wind_speed)",
    )

    input_Virtual_RE_config: str = Field(
        title="Path to virtual RE configuration file solar_config.yml",
        default="/home/shared_storage/solar_config.yml",
        description="YAML file containing configuration for virtual solar generation.",
    )


class OutputModel(BaseModel):
    """
    SolarSimPiece Output Model
    """
    output_path: str = Field(
        title="Virtual solar CSV output path",
        description="Path to generated virtual solar data CSV file.",
    )