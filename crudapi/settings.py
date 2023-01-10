from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    log_level: str = Field(env="LOG_LEVEL", default="INFO")
    api_host: str = Field(env="CRUDAPI_HOST", default="0.0.0.0")
    api_port: int = Field(env="CRUDAPI_PORT", default=8000)
