"""
POST /api/chat: приём сообщения, стриминг ответа LLM по SSE, сохранение в БД.
"""
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from httpx import HTTPStatusError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.llm import load_system_prompt, stream_chat
from app.models import Message
from app.schemas import ChatRequest

router = APIRouter(prefix="/api", tags=["chat"])


def _sse_message(data: str) -> str:
    """Формирует одну SSE-строку: data: <content>."""
    return f"data: {data}\n\n"


async def _get_history(session: AsyncSession, user_id: str, dialog_id: str) -> list[dict[str, str]]:
    """Загружает историю сообщений для user_id и dialog_id из БД (роль + content)."""
    result = await session.execute(
        select(Message.role, Message.content).where(
            Message.user_id == user_id,
            Message.dialog_id == dialog_id,
        ).order_by(Message.created_at)
    )
    return [{"role": row.role, "content": row.content} for row in result.all()]


@router.post("/chat")
async def chat(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Принимает user_id и message, возвращает SSE-поток с ответом LLM.
    После завершения стрима сохраняет сообщение пользователя и ответ ассистента в PostgreSQL.
    При ошибке LLM — 502/503; сохраняем только сообщение пользователя без ответа ассистента.
    При обрыве соединения клиентом — не сохраняем частичный ответ.
    """
    settings = get_settings()
    try:
        system_prompt = load_system_prompt(settings.prompt_path)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Файл промпта недоступен")

    history = await _get_history(db, body.user_id, body.dialog_id)
    messages = [*history, {"role": "user", "content": body.message}]

    user_msg = Message(
        user_id=body.user_id,
        dialog_id=body.dialog_id,
        role="user",
        content=body.message,
    )
    db.add(user_msg)
    await db.flush()

    async def stream_and_save() -> AsyncIterator[bytes]:
        full_reply: list[str] = []
        try:
            async for chunk in stream_chat(messages, system_prompt=system_prompt):
                full_reply.append(chunk)
                yield _sse_message(chunk).encode("utf-8")
            yield _sse_message("[DONE]").encode("utf-8")
            assistant_msg = Message(
                user_id=body.user_id,
                dialog_id=body.dialog_id,
                role="assistant",
                content="".join(full_reply),
            )
            db.add(assistant_msg)
            await db.commit()
        except HTTPStatusError as e:
            await db.commit()
            raise HTTPException(
                status_code=503 if e.response.status_code >= 500 else 502,
                detail="Ошибка LLM",
            )
        except Exception:
            await db.commit()
            raise

    return StreamingResponse(
        stream_and_save(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
