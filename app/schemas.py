"""
Pydantic-схемы для API: запрос отправки сообщения.
"""
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=255, description="Идентификатор пользователя")
    message: str = Field(..., min_length=1, description="Текст сообщения пользователя")
    dialog_id: str = Field(default="default", max_length=255, description="Идентификатор диалога (опционально)")
