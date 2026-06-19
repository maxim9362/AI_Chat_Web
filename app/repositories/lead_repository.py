# Этот файл содержит операции создания и чтения лидов из базы данных.

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.lead import Lead


def get_lead_by_session_id(
    db: Session,
    session_id: str,
) -> Lead | None:
    return db.scalar(
        select(Lead).where(Lead.session_id == session_id)
    )


def create_lead(
    db: Session,
    session_id: str,
    name: str,
    phone: str | None,
    email: str | None,
    message: str | None,
    preferred_contact_time: str | None = None,
) -> Lead:
    lead = Lead(
        session_id=session_id,
        name=name,
        phone=phone,
        email=email,
        message=message,
        preferred_contact_time=preferred_contact_time,
        status="new",
    )
    db.add(lead)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing_lead = get_lead_by_session_id(db, session_id)
        if existing_lead is None:
            raise
        return existing_lead

    db.refresh(lead)
    return lead


def update_lead(
    db: Session,
    lead: Lead,
    name: str,
    phone: str | None,
    email: str | None,
    message: str | None,
    preferred_contact_time: str | None = None,
) -> Lead:
    lead.name = name
    lead.phone = phone
    lead.email = email
    lead.message = message
    lead.preferred_contact_time = preferred_contact_time
    db.commit()
    db.refresh(lead)
    return lead


def append_lead_message(
    db: Session,
    lead: Lead,
    additional_details: str,
) -> Lead:
    normalized_details = additional_details.strip()
    if not normalized_details:
        return lead

    existing_message = (lead.message or "").strip()
    if normalized_details.casefold() in existing_message.casefold():
        return lead

    lead.message = (
        f"{existing_message}\nДополнение: {normalized_details}"
        if existing_message
        else f"Дополнение: {normalized_details}"
    )
    db.commit()
    db.refresh(lead)
    return lead


def list_leads(db: Session) -> list[Lead]:
    statement = select(Lead).order_by(
        Lead.created_at.desc(),
        Lead.id.desc(),
    )
    return list(db.scalars(statement))
