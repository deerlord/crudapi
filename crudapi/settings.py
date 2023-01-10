from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    log_level: str = Field(env="LOG_LEVEL", default="INFO")
    api_host: str = Field(env="CRUD_API", default="0.0.0.0")
    api_port: int = Field(env="CRUD_PORT", default=8000)
