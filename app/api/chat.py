# Этот файл содержит HTTP-маршрут базового чата.

from fastapi import APIRouter

from app.schemas.chat import ChatRequest, ChatResponse


router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest) -> ChatResponse:
    return ChatResponse(
        session_id=payload.session_id,
        reply=f"Сообщение получено: {payload.message}",
    )
