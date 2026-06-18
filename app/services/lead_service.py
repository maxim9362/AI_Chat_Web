# Этот файл проверяет данные лида и создает одну заявку на пользовательскую сессию.

from collections.abc import Iterable

from sqlalchemy.orm import Session

from app.models.lead import Lead
from app.repositories.lead_repository import (
    create_lead,
    get_lead_by_session_id,
    update_lead,
)
from app.services.lead_extractor import extract_lead_data


def create_lead_if_ready(
    db: Session,
    session_id: str,
    user_messages: Iterable[str],
    details: str | None = None,
) -> Lead | None:
    extracted = extract_lead_data(user_messages)
    has_contact = bool(extracted.phone or extracted.email)
    if not extracted.name or not has_contact or not extracted.service:
        return None

    return create_or_update_lead(
        db=db,
        session_id=session_id,
        name=extracted.name,
        phone=extracted.phone,
        email=extracted.email,
        details=details or extracted.service,
    )


def create_or_update_lead(
    db: Session,
    session_id: str,
    name: str,
    phone: str | None,
    email: str | None,
    details: str,
) -> Lead:
    existing_lead = get_lead_by_session_id(db, session_id)
    if existing_lead is not None:
        return update_lead(
            db=db,
            lead=existing_lead,
            name=name,
            phone=phone,
            email=email,
            message=details,
        )

    return create_lead(
        db=db,
        session_id=session_id,
        name=name,
        phone=phone,
        email=email,
        message=details,
    )
