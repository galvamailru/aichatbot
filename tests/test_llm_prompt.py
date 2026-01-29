"""
Тесты загрузки промпта из файла (без вызова LLM).
"""
from pathlib import Path

import pytest

from app.llm import load_system_prompt


def test_load_system_prompt_reads_file(tmp_path):
    """load_system_prompt возвращает содержимое файла."""
    p = tmp_path / "p.txt"
    p.write_text("  Hello world  ", encoding="utf-8")
    assert load_system_prompt(p) == "Hello world"


def test_load_system_prompt_raises_if_not_found():
    """Если файл не найден — FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_system_prompt(Path("/nonexistent/file.txt"))
