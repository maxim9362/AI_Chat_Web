# Этот файл ведет пользователя по последовательным шагам оформления заявки.

from collections.abc import Sequence
from dataclasses import dataclass
import re
from typing import Protocol

from sqlalchemy.orm import Session

from app.services.lead_extractor import (
    extract_email,
    extract_lead_data,
    extract_phone,
    extract_service,
)
from app.services.lead_service import create_or_update_lead
from app.repositories.lead_repository import get_lead_by_session_id


class DialogueMessage(Protocol):
    role: str
    content: str


LEAD_INTENT_PATTERN = re.compile(
    r"(?:\b(?:записаться|запишите|заявк\w*|перезвон\w*)\b|"
    r"связаться\s+со\s+специалист\w*|"
    r"(?:нужна|нужен|хочу|требуется)\s+"
    r"(?:консультац\w*|помощ\w*\s+специалист\w*))",
    re.IGNORECASE,
)
SIMPLE_NAME_PATTERN = re.compile(
    r"^[А-ЯЁA-Z][а-яёa-z]{1,30}"
    r"(?:[\s-][А-ЯЁA-Z][а-яёa-z]{1,30}){0,2}$",
    re.IGNORECASE,
)
TIME_PATTERN = re.compile(
    r"(?:\b(?:сегодня|завтра|послезавтра|утром|днем|днём|вечером|"
    r"будни|выходн\w*)\b|\b(?:[01]?\d|2[0-3])[:.][0-5]\d\b|"
    r"\b(?:понедельник|вторник|сред\w*|четверг|пятниц\w*|"
    r"суббот\w*|воскресень\w*)\b)",
    re.IGNORECASE,
)

ASK_NAME = "Как к вам обращаться?"
ASK_CONTACT = "Оставьте, пожалуйста, номер телефона или email для связи."
ASK_TASK = (
    "Кратко опишите задачу. Например: нужна диагностика, ремонт двери, "
    "сборка мебели или установка карниза."
)
ASK_TIME = (
    "Когда вам удобно принять звонок? Укажите день или время, "
    "например: завтра после 15:00."
)
CLARIFY_NAME = "Не удалось распознать имя. Напишите, пожалуйста, только ваше имя."
CLARIFY_CONTACT = (
    "Не удалось распознать контакт. Укажите телефон из 10–11 цифр "
    "или email, например name@example.com."
)
CLARIFY_TASK = (
    "Не удалось понять задачу. Уточните, пожалуйста, что именно требуется: "
    "диагностика, ремонт, сборка мебели, установка или обслуживание."
)
CLARIFY_TIME = (
    "Не удалось понять удобное время. Напишите, например: "
    "завтра после 15:00 или в пятницу утром."
)
LEAD_CREATED = (
    "Спасибо, заявка оформлена. Менеджер свяжется с вами "
    "по указанному контакту в удобное время."
)


@dataclass(frozen=True, slots=True)
class LeadDialogueState:
    active: bool
    name: str | None
    phone: str | None
    email: str | None
    service: str | None
    preferred_time: str | None
    expected_step: str | None


def process_lead_dialogue(
    db: Session,
    session_id: str,
    messages: Sequence[DialogueMessage],
) -> str | None:
    existing_lead = get_lead_by_session_id(db, session_id)
    if (
        existing_lead is not None
        and existing_lead.message
        and "Удобное время:" in existing_lead.message
    ):
        return None

    state = _build_state(messages)
    if not state.active:
        return None

    latest_user_message = next(
        (
            message.content.strip()
            for message in reversed(messages)
            if message.role == "user"
        ),
        "",
    )

    if not state.name:
        return (
            CLARIFY_NAME
            if state.expected_step == "name" and latest_user_message
            else ASK_NAME
        )

    if not (state.phone or state.email):
        return (
            CLARIFY_CONTACT
            if state.expected_step == "contact" and latest_user_message
            else ASK_CONTACT
        )

    if not state.service:
        return (
            CLARIFY_TASK
            if state.expected_step == "task" and latest_user_message
            else ASK_TASK
        )

    if not state.preferred_time:
        return (
            CLARIFY_TIME
            if state.expected_step == "time" and latest_user_message
            else ASK_TIME
        )

    details = (
        f"Услуга: {state.service}. "
        f"Удобное время: {state.preferred_time}."
    )
    create_or_update_lead(
        db=db,
        session_id=session_id,
        name=state.name,
        phone=state.phone,
        email=state.email,
        details=details,
    )
    return LEAD_CREATED


def _build_state(messages: Sequence[DialogueMessage]) -> LeadDialogueState:
    user_messages = [
        message.content.strip()
        for message in messages
        if message.role == "user" and message.content.strip()
    ]
    extracted = extract_lead_data(user_messages)
    active = any(
        LEAD_INTENT_PATTERN.search(message)
        for message in user_messages
    ) or any(
        message.role == "assistant"
        and message.content in {ASK_NAME, ASK_CONTACT, ASK_TASK, ASK_TIME}
        for message in messages
    )

    name = extracted.name
    phone = extracted.phone
    email = extracted.email
    service = (
        extracted.service
        if extracted.service and extracted.service != "консультация"
        else None
    )
    preferred_time: str | None = None
    expected_step: str | None = None

    for index, message in enumerate(messages):
        if message.role != "assistant":
            continue

        step = _step_for_prompt(message.content)
        if step is None:
            continue

        expected_step = step
        next_user_message = _next_user_message(messages, index + 1)
        if next_user_message is None:
            continue

        if step == "name":
            parsed_name = _parse_name_answer(next_user_message)
            if parsed_name:
                name = parsed_name
                expected_step = None
            phone = phone or extract_phone(next_user_message)
            email = email or extract_email(next_user_message)
        elif step == "contact":
            phone = phone or extract_phone(next_user_message)
            email = email or extract_email(next_user_message)
            if phone or email:
                expected_step = None
        elif step == "task":
            parsed_service = extract_service(next_user_message)
            if parsed_service and parsed_service != "консультация":
                service = parsed_service
                expected_step = None
        elif step == "time" and TIME_PATTERN.search(next_user_message):
            preferred_time = next_user_message.strip()
            expected_step = None

    return LeadDialogueState(
        active=active,
        name=name,
        phone=phone,
        email=email,
        service=service,
        preferred_time=preferred_time,
        expected_step=expected_step,
    )


def _step_for_prompt(content: str) -> str | None:
    prompts = {
        ASK_NAME: "name",
        CLARIFY_NAME: "name",
        ASK_CONTACT: "contact",
        CLARIFY_CONTACT: "contact",
        ASK_TASK: "task",
        CLARIFY_TASK: "task",
        ASK_TIME: "time",
        CLARIFY_TIME: "time",
    }
    return prompts.get(content)


def _next_user_message(
    messages: Sequence[DialogueMessage],
    start_index: int,
) -> str | None:
    for message in messages[start_index:]:
        if message.role == "assistant":
            return None
        if message.role == "user":
            return message.content.strip()
    return None


def _parse_name_answer(text: str) -> str | None:
    without_contacts = re.sub(
        r"(?:\+7|8|7)?[\s(.-]*(?:\d[\s()\-]*){10}",
        "",
        text,
    )
    candidate = re.split(r"[,;]|\d", without_contacts, maxsplit=1)[0].strip()
    if not SIMPLE_NAME_PATTERN.fullmatch(candidate):
        return None
    return " ".join(part.capitalize() for part in candidate.split())
