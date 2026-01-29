"""
HTTP-клиент к LLM DeepSeek с поддержкой стриминга. URL и ключ только из конфигурации (.env).
"""
import json
from pathlib import Path
from typing import AsyncIterator

import httpx

from app.config import get_settings


def load_system_prompt(path: Path) -> str:
    """Читает системный промпт только из файла. Путь из конфигурации."""
    if not path.exists():
        raise FileNotFoundError(f"Файл промпта не найден: {path}")
    return path.read_text(encoding="utf-8").strip()


async def stream_chat(
    messages: list[dict[str, str]],
    *,
    system_prompt: str,
) -> AsyncIterator[str]:
    """
    Вызов DeepSeek chat/completions со stream=True.
    Yields фрагменты content из delta.
    При ошибке LLM пробрасывает httpx.HTTPStatusError (502/503).
    """
    settings = get_settings()
    url = f"{settings.LLM_URL.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": settings.LLM_MODEL,
        "messages": [{"role": "system", "content": system_prompt}, *messages],
        "stream": True,
    }
    def _is_word_char(c: str) -> bool:
        if not c:
            return False
        code = ord(c)
        return (
            (0x30 <= code <= 0x39)
            or (0x41 <= code <= 0x5A)
            or (0x61 <= code <= 0x7A)
            or (0x0400 <= code <= 0x04FF)
            or c == "_"
        )

    last_ends_with_space = True
    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream("POST", url, json=body, headers=headers) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line or line.strip() != line:
                    continue
                if line.startswith("data: "):
                    data = line[6:].strip()
                    if data == "[DONE]":
                        return
                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    choices = chunk.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta") or {}
                    content = delta.get("content")
                    if content:
                        if not last_ends_with_space and content and _is_word_char(content[0]):
                            yield " "
                        yield content
                        last_ends_with_space = content[-1].isspace() if content else last_ends_with_space
