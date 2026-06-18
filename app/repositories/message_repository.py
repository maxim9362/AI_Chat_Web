# Этот файл содержит операции сохранения и чтения сообщений из базы данных.

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.message import Message


def save_message(
    db: Session,
    session_id: str,
    role: str,
    content: str,
) -> Message:
    message = Message(
        session_id=session_id,
        role=role,
        content=content,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def get_recent_messages(
    db: Session,
    session_id: str,
    limit: int = 6,
) -> list[Message]:
    if limit < 1:
        return []

    statement = (
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.desc(), Message.id.desc())
        .limit(limit)
    )
    messages = list(db.scalars(statement))
    messages.reverse()
    return messages
