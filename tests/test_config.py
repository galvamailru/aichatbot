"""
Тесты конфигурации: чтение из .env, путь к промпту.
"""
from pathlib import Path

import pytest

from app.config import Settings, get_settings


def test_settings_loads_from_env(monkeypatch):
    """Переменные окружения попадают в Settings."""
    monkeypatch.setenv("POSTGRES_HOST", "dbhost")
    monkeypatch.setenv("POSTGRES_DB", "mydb")
    monkeypatch.setenv("LLM_URL", "https://custom.llm")
    s = get_settings()
    assert s.POSTGRES_HOST == "dbhost"
    assert s.POSTGRES_DB == "mydb"
    assert s.LLM_URL == "https://custom.llm"


def test_prompt_path_resolution(monkeypatch, tmp_path):
    """PROMPT_FILE_PATH разрешается относительно корня проекта или абсолютно."""
    p = tmp_path / "prompt.txt"
    p.write_text("x")
    monkeypatch.setenv("PROMPT_FILE_PATH", str(p))
    s = get_settings()
    assert s.prompt_path == p
    assert s.prompt_path.exists()
