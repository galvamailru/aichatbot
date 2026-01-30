"""
Админ API: список сессий, история чата по сессии, список лидов, агрегация по дате.
Доступ по заголовку X-Admin-Key (значение из .env ADMIN_KEY).
"""
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import cast, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models import Lead, Message

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _require_admin_key(x_admin_key: str | None = Header(None, alias="X-Admin-Key")) -> str:
    settings = get_settings()
    if not settings.ADMIN_KEY or x_admin_key != settings.ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Неверный или отсутствующий ключ админки")
    return x_admin_key


@router.get("/sessions")
async def list_sessions(
    _: str = Depends(_require_admin_key),
    db: AsyncSession = Depends(get_db),
):
    """Список сессий: пары (user_id, dialog_id) с датой последнего сообщения."""
    q = (
        select(Message.user_id, Message.dialog_id, func.max(Message.created_at).label("last_at"))
        .group_by(Message.user_id, Message.dialog_id)
        .order_by(func.max(Message.created_at).desc())
    )
    result = await db.execute(q)
    rows = result.all()
    return [
        {"user_id": r.user_id, "dialog_id": r.dialog_id, "last_at": r.last_at.isoformat() if r.last_at else None}
        for r in rows
    ]


@router.get("/sessions/{user_id}/{dialog_id}/messages")
async def get_session_messages(
    user_id: str,
    dialog_id: str,
    _: str = Depends(_require_admin_key),
    db: AsyncSession = Depends(get_db),
):
    """История чата по сессии (user_id + dialog_id)."""
    q = (
        select(Message.role, Message.content, Message.created_at)
        .where(Message.user_id == user_id, Message.dialog_id == dialog_id)
        .order_by(Message.created_at)
    )
    result = await db.execute(q)
    rows = result.all()
    return [
        {"role": r.role, "content": r.content, "created_at": r.created_at.isoformat() if r.created_at else None}
        for r in rows
    ]


@router.get("/stats")
async def list_stats(
    _: str = Depends(_require_admin_key),
    db: AsyncSession = Depends(get_db),
):
    """Агрегация по дате: дата, количество уникальных пользователей, количество сессий (диалогов)."""
    from sqlalchemy import Date
    day_col = cast(Message.created_at, Date)
    subq = (
        select(Message.user_id, Message.dialog_id, day_col.label("day"))
        .where(Message.created_at.isnot(None))
        .group_by(Message.user_id, Message.dialog_id, day_col)
    ).subquery()
    q = (
        select(subq.c.day, func.count(subq.c.user_id).label("sessions"), func.count(func.distinct(subq.c.user_id)).label("unique_users"))
        .group_by(subq.c.day)
        .order_by(subq.c.day.desc())
    )
    result = await db.execute(q)
    rows = result.all()
    return [
        {"day": r.day.isoformat() if r.day else None, "sessions": r.sessions, "unique_users": r.unique_users}
        for r in rows
    ]


@router.get("/leads")
async def list_leads(
    _: str = Depends(_require_admin_key),
    db: AsyncSession = Depends(get_db),
):
    """Список лидов (контакты для обратной связи)."""
    q = select(Lead).order_by(Lead.created_at.desc())
    result = await db.execute(q)
    leads = result.scalars().all()
    return [
        {
            "id": str(l.id),
            "user_id": l.user_id,
            "dialog_id": l.dialog_id,
            "contact_text": l.contact_text,
            "created_at": l.created_at.isoformat() if l.created_at else None,
            "updated_at": l.updated_at.isoformat() if getattr(l, "updated_at", None) else None,
        }
        for l in leads
    ]
