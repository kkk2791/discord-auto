import os
from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }

    # Application
    app_name: str = Field(default="DiscordAuto", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    app_debug: bool = Field(default=True, alias="APP_DEBUG")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    app_secret_key: str = Field(default="change-me", alias="APP_SECRET_KEY")

    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/discord_auto.db",
        alias="DATABASE_URL",
    )

    # DeepSeek
    deepseek_api_key: str = Field(default="", alias="DEEPSEEK_API_KEY")
    deepseek_base_url: str = Field(
        default="https://api.deepseek.com", alias="DEEPSEEK_BASE_URL"
    )
    deepseek_model: str = Field(default="deepseek-chat", alias="DEEPSEEK_MODEL")

    # Scheduler
    scheduler_timezone: str = Field(
        default="Asia/Shanghai", alias="SCHEDULER_TIMEZONE"
    )
    scheduler_max_workers: int = Field(default=10, alias="SCHEDULER_MAX_WORKERS")

    # Logging
    log_level: str = Field(default="DEBUG", alias="LOG_LEVEL")
    log_dir: str = Field(default="./logs", alias="LOG_DIR")

    @property
    def data_dir(self) -> Path:
        return Path("data")

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
