"""
Конфигурация приложения. Все переменные читаются только из .env.
"""
import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _resolve_prompt_path(v: str) -> Path:
    p = Path(v)
    if not p.is_absolute():
        p = Path(__file__).resolve().parent.parent / p
    return p


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "aichatbot"
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = "aichatbot"

    LLM_URL: str = "https://api.deepseek.com"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "deepseek-chat"
    LLM_TEMPERATURE: float = 0.7

    PROMPT_FILE_PATH: str = "prompts/system.txt"
    ADMIN_KEY: str = ""

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def prompt_path(self) -> Path:
        return _resolve_prompt_path(self.PROMPT_FILE_PATH)


def get_settings() -> Settings:
    return Settings()
