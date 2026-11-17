from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Invoice Manager"
    secret_key: str = "change-me-in-production"
    database_url: str = "sqlite:///./data/invoice_manager.db"
    session_https_only: bool = False
    page_size: int = 20
    source_systems: str = "Sistema A,Sistema B"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="INVOICE_", extra="ignore")

    @property
    def database_path(self) -> Path:
        return Path(self.database_url.removeprefix("sqlite:///"))

    @property
    def configured_sources(self) -> list[str]:
        return [name.strip() for name in self.source_systems.split(",") if name.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
