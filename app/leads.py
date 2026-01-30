"""
Извлечение контактов для обратной связи из сообщений пользователя.
Один лид на сессию (user_id, dialog_id): при повторном вводе контакта обновляем запись (последний корректный контакт).
В одном сообщении может быть несколько контактов (email и телефон) — сохраняем все в contact_text через « | ».
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


def extract_contact_text(text: str) -> str | None:
    """
    Извлекает контактную информацию (email и/или телефон) из текста.
    Возвращает строку с найденными контактами или None, если ничего не найдено.
    """
    parts = []
    for m in EMAIL_RE.finditer(text):
        parts.append(m.group(0))
    for m in PHONE_RE.finditer(text):
        parts.append(m.group(0).strip())
    if not parts:
        return None
    return " | ".join(parts)


async def save_lead_if_contact(
    db: AsyncSession,
    user_id: str,
    dialog_id: str,
    user_message: str,
) -> bool:
    """
    Если в сообщении пользователя есть контакты (email/телефон), сохраняет или обновляет лид.
    Один лид на сессию (user_id, dialog_id): при повторном вводе обновляем contact_text на последний.
    В contact_text может быть несколько контактов через « | ».
    Возвращает True, если лид сохранён или обновлён.
    """
    contact = extract_contact_text(user_message)
    if not contact:
        return False
    result = await db.execute(
        select(Lead).where(Lead.user_id == user_id, Lead.dialog_id == dialog_id)
    )
    existing = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if existing:
        existing.contact_text = contact
        existing.updated_at = now
        await db.flush()
        return True
    lead = Lead(
        id=uuid4(),
        user_id=user_id,
        dialog_id=dialog_id,
        contact_text=contact,
        created_at=now,
        updated_at=now,
    )
    db.add(lead)
    await db.flush()
    return True
