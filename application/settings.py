from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    log_level: str = Field(env="LOG_LEVEL", default="INFO")
