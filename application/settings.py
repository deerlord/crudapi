from typing import Optional

from pydantic import BaseSettings, Field, PositiveInt


class Settings(BaseSettings):
    log_level: str = Field(env="LOG_LEVEL", default="INFO")
    database_protocol: str = Field(env="DATABASE_PROTOCOL", default="sqlite")
    database_name: str = Field(env="DATABASE_NAME", default="/data.sqlite")
    database_username: Optional[str] = Field(env="DATABASE_USERNAME", default=None)
    database_password: Optional[str] = Field(env="DATABASE_PASSWORD", default=None)
    database_hostname: Optional[str] = Field(env="DATABASE_HOSTNAME", default=None)
    database_port: Optional[PositiveInt] = Field(env="DATABASE_PORT", default=None)

    class Config:
        env_file = "/secrets/.env"
