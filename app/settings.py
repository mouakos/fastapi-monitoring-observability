"""Configuration settings for the FastAPI application."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    """Configuration settings for the FastAPI application."""

    log_level: str = "INFO"
    log_format: str = "text"
    log_to_file: bool = False

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False
    )


config = AppConfig()
