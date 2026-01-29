"""
Тесты API чата: валидация (400/422), ответ 500 при отсутствии файла промпта.
Стриминг и сохранение в БД проверяются при моке LLM и тестовой БД (опционально).
"""
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.database import get_db
from app.main import app


@pytest.fixture
def client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _mock_db_session():
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    try:
        yield session
    finally:
        pass


@pytest.fixture
def prompt_file(tmp_path, monkeypatch):
    """Файл промпта и переменная окружения."""
    p = tmp_path / "system.txt"
    p.write_text("Test assistant.", encoding="utf-8")
    monkeypatch.setenv("PROMPT_FILE_PATH", str(p))
    return p


@pytest.mark.asyncio
async def test_chat_validates_user_id_empty(client):
    """Пустой user_id — 422."""
    r = await client.post(
        "/api/chat",
        json={"user_id": "", "message": "hi", "dialog_id": "default"},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_chat_validates_message_empty(client):
    """Пустое message — 422."""
    r = await client.post(
        "/api/chat",
        json={"user_id": "u1", "message": "", "dialog_id": "default"},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_chat_prompt_file_not_found_returns_500(client, monkeypatch):
    """Если файл промпта недоступен — 500."""
    monkeypatch.setenv("PROMPT_FILE_PATH", "/nonexistent/prompt.txt")
    app.dependency_overrides[get_db] = _mock_db_session
    try:
        r = await client.post(
            "/api/chat",
            json={"user_id": "u1", "message": "hello", "dialog_id": "default"},
        )
        assert r.status_code == 500
        data = r.json()
        assert "detail" in data
    finally:
        app.dependency_overrides.pop(get_db, None)
