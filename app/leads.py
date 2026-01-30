"""
Извлечение контактов для обратной связи из сообщений пользователя.
Один лид на сессию (user_id, dialog_id): контакты накапливаются — телефон, почта и др. (без дубликатов).
"""
import re
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Lead

# Email и телефон (русский/международный формат)
EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    re.IGNORECASE,
)
PHONE_RE = re.compile(
    r"(?:\+7|8)?[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}"
    r"|\+\d{1,3}[\s\-]?\d{2,3}[\s\-]?\d{2,3}[\s\-]?\d{2,4}",
)


def _extract_contact_parts(text: str) -> list[str]:
    """Извлекает все контакты (email, телефон) из текста как список уникальных строк."""
    parts = []
    seen = set()
    for m in EMAIL_RE.finditer(text):
        s = m.group(0).strip().lower()
        if s and s not in seen:
            seen.add(s)
            parts.append(m.group(0).strip())
    for m in PHONE_RE.finditer(text):
        s = _normalize_contact(m.group(0))
        if s and s not in seen:
            seen.add(s)
            parts.append(m.group(0).strip())
    return parts


def extract_contact_text(text: str) -> str | None:
    """
    Извлекает контактную информацию (email и/или телефон) из текста.
    Возвращает строку с найденными контактами или None, если ничего не найдено.
    """
    parts = _extract_contact_parts(text)
    if not parts:
        return None
    return " | ".join(parts)


def _merge_contacts(existing_text: str | None, new_parts: list[str]) -> str:
    """Объединяет уже сохранённые контакты с новыми (без дубликатов), порядок: существующие + новые."""
    seen = set()
    parts = []
    if existing_text:
        for p in (x.strip() for x in existing_text.split(" | ") if x.strip()):
            p_norm = _normalize_contact(p)
            if p_norm and p_norm not in seen:
                seen.add(p_norm)
                parts.append(p.strip())
    for p in new_parts:
        p = p.strip()
        if not p:
            continue
        p_norm = _normalize_contact(p)
        if p_norm and p_norm not in seen:
            seen.add(p_norm)
            parts.append(p)
    return " | ".join(parts)


def _normalize_contact(s: str) -> str:
    """Нормализация для сравнения (убираем пробелы/дефисы в цифрах и нижний регистр для email)."""
    s = s.strip().lower()
    digits = "".join(c for c in s if c.isdigit() or c == "+")
    if digits:
        return digits
    return s


async def save_lead_if_contact(
    db: AsyncSession,
    user_id: str,
    dialog_id: str,
    user_message: str,
) -> bool:
    """
    Если в сообщении пользователя есть контакты (email/телефон и т.д.), сохраняет или обновляет лид.
    Один лид на сессию (user_id, dialog_id): контакты накапливаются — телефон, почта и др. (без дубликатов).
    Возвращает True, если лид сохранён или обновлён.
    """
    new_parts = _extract_contact_parts(user_message)
    if not new_parts:
        return False
    result = await db.execute(
        select(Lead).where(Lead.user_id == user_id, Lead.dialog_id == dialog_id)
    )
    existing = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if existing:
        merged = _merge_contacts(existing.contact_text, new_parts)
        if merged == existing.contact_text:
            return False
        existing.contact_text = merged
        existing.updated_at = now
        await db.flush()
        return True
    lead = Lead(
        id=uuid4(),
        user_id=user_id,
        dialog_id=dialog_id,
        contact_text=" | ".join(p.strip() for p in new_parts),
        created_at=now,
        updated_at=now,
    )
    db.add(lead)
    await db.flush()
    return True
