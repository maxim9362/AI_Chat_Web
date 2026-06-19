# Этот файл ведет клиента по шагам оформления заявки на обслуживание кондиционера.

from collections.abc import Sequence
from dataclasses import dataclass
import re
from typing import Protocol

from sqlalchemy.orm import Session

from app.repositories.lead_repository import get_lead_by_session_id
from app.services.lead_extractor import (
    extract_email,
    extract_lead_data,
    extract_phone,
    extract_preferred_contact_time,
    extract_service,
    is_incomplete_contact_time,
    normalize_air_conditioner_text,
)
from app.services.lead_service import (
    create_or_update_lead,
    format_lead_confirmation,
)


class DialogueMessage(Protocol):
    role: str
    content: str


LEAD_INTENT_PATTERN = re.compile(
    r"(?:\b(?:записаться|запишите|заявк\w*|перезвон\w*)\b|"
    r"связаться\s+со\s+(?:специалист\w*|мастер\w*)|"
    r"(?:нужна|нужен|хочу|требуется)\s+консультац\w*|"
    r"\b(?:ремонт|установк\w*|монтаж|чистк\w*|заправк\w*|"
    r"диагностик\w*|демонтаж)\b.*\bкондиционер\w*|"
    r"\bкондиционер\w*.*\b(?:не\s+охлаждает|течет|шумит|"
    r"не\s+включается|цена|стоимость)\b)",
    re.IGNORECASE,
)
SIMPLE_NAME_PATTERN = re.compile(
    r"^[А-ЯЁA-Z][а-яёa-z]{1,30}"
    r"(?:[\s-][А-ЯЁA-Z][а-яёa-z]{1,30}){0,2}$",
    re.IGNORECASE,
)
PRICE_PATTERN = re.compile(r"\b(?:цен\w*|стоит|стоимость|сколько)\b", re.IGNORECASE)
AFFIRMATIVE_PATTERN = re.compile(
    r"^(?:да|давайте|хочу|оформляйте|оформить|запишите|можно|хорошо|ок|окей)"
    r"[!,.?\s]*$",
    re.IGNORECASE,
)
NEGATIVE_PATTERN = re.compile(
    r"^(?:нет|не\s+нужно|не\s+сейчас|пока\s+нет|отмена)[!,.?\s]*$",
    re.IGNORECASE,
)
PROBLEM_PATTERN = re.compile(
    r"(?:не\s+охлаждает|не\s+греет|не\s+включается|не\s+работает|"
    r"течет|течёт|капает|шумит|вибрирует|пахнет|запах|"
    r"выбивает|ошибк\w*|обмерз\w*|лед|лёд|слабо\s+дует)",
    re.IGNORECASE,
)
CITY_ALIASES = {
    "ашдод": "Ашдод",
    "ашкелон": "Ашкелон",
    "ган явне": "Ган-Явне",
    "ган-явне": "Ган-Явне",
    "явне": "Явне",
    "кириат малахи": "Кирьят-Малахи",
    "кириат-малахи": "Кирьят-Малахи",
    "кирьят малахи": "Кирьят-Малахи",
    "кирьят-малахи": "Кирьят-Малахи",
}

ASK_TASK = (
    "Конечно, помогу. Что именно нужно: ремонт, установка, чистка, "
    "заправка газа, диагностика или демонтаж кондиционера?"
)
ASK_PROBLEM = (
    "Что именно происходит с кондиционером: не охлаждает, течет вода, "
    "шумит, пахнет, не включается или показывает ошибку?"
)
REPAIR_PRICE_AND_PROBLEM = (
    "Обычно ремонт кондиционера начинается примерно от 250 ₪. "
    "Точную стоимость можно узнать после консультации со специалистом или "
    "проверки мастером: она зависит от причины поломки, модели кондиционера "
    "и сложности доступа. "
    "Что именно происходит: не охлаждает, течет, шумит или не включается?"
)
DIAGNOSTICS_PRICE_AND_CITY = (
    "Выезд и диагностика обычно стоят примерно 150–250 ₪. "
    "Точную стоимость можно узнать после консультации со специалистом или "
    "проверки мастером: она зависит от причины проблемы, модели кондиционера "
    "и сложности доступа. Подскажите, пожалуйста, в каком городе нужен мастер?"
)
CLEANING_PRICE_AND_CITY = (
    "Профилактическая чистка обычно стоит примерно 250–400 ₪. "
    "Точную стоимость можно узнать после консультации со специалистом: она "
    "зависит от модели, степени загрязнения и сложности доступа. "
    "Подскажите, пожалуйста, в каком городе находится кондиционер?"
)
GAS_PRICE_AND_CITY = (
    "Заправка газа обычно стоит примерно 350–600 ₪. "
    "Точную стоимость можно узнать после проверки специалистом: она зависит "
    "от модели, типа газа, объема и наличия утечки. "
    "Подскажите, пожалуйста, в каком городе находится кондиционер?"
)
INSTALLATION_PRICE_AND_CITY = (
    "Стандартная установка начинается примерно от 900 ₪. "
    "Точную стоимость можно узнать после консультации со специалистом: она "
    "зависит от модели, длины трассы, стены и сложности доступа. "
    "Подскажите, пожалуйста, в каком городе планируется установка?"
)
DISMANTLING_PRICE_AND_CITY = (
    "Демонтаж обычно стоит примерно 300–600 ₪. "
    "Точную стоимость можно узнать после проверки специалистом: она зависит "
    "от модели, высоты, крепления и сложности доступа. "
    "Подскажите, пожалуйста, в каком городе находится объект?"
)
PRICE_PROMPTS = {
    "ремонт кондиционера": REPAIR_PRICE_AND_PROBLEM,
    "диагностика кондиционера": DIAGNOSTICS_PRICE_AND_CITY,
    "чистка кондиционера": CLEANING_PRICE_AND_CITY,
    "заправка газа": GAS_PRICE_AND_CITY,
    "установка кондиционера": INSTALLATION_PRICE_AND_CITY,
    "демонтаж кондиционера": DISMANTLING_PRICE_AND_CITY,
}
ASK_CITY = (
    "В каком городе находится кондиционер: Ашдод, Ашкелон, "
    "Ган-Явне, Явне или Кирьят-Малахи?"
)
OFFER_BOOKING = (
    "Мы работаем в этом городе. Хотите, я оформлю заявку мастеру "
    "для уточнения стоимости и времени выезда?"
)
BOOKING_DECLINED = (
    "Хорошо, заявку пока не оформляю. Можете продолжить задавать вопросы, "
    "я постараюсь помочь."
)
ASK_NAME = "Как к вам обращаться?"
ASK_CONTACT = "Оставьте, пожалуйста, номер телефона или email для связи."
ASK_CONTACT_TIME = (
    "Когда вам удобно, чтобы с вами связался мастер или менеджер? "
    "Например: сегодня после 17:00, завтра утром или в любое время."
)
CLARIFY_TASK = (
    "Не совсем понял услугу. Напишите один вариант: ремонт, установка, "
    "чистка, заправка газа, диагностика или демонтаж."
)
CLARIFY_PROBLEM = (
    "Уточните, пожалуйста, симптом: кондиционер не охлаждает, течет, "
    "шумит, пахнет, не включается или показывает ошибку?"
)
CLARIFY_CITY = (
    "Не удалось распознать город. Мы работаем в Ашдоде, Ашкелоне, "
    "Ган-Явне, Явне и Кирьят-Малахи. В каком городе нужен мастер?"
)
CLARIFY_NAME = "Не удалось распознать имя. Напишите, пожалуйста, только ваше имя."
CLARIFY_CONTACT = (
    "Не удалось распознать контакт. Укажите корректный израильский мобильный "
    "номер, например 0501234567 или +972501234567, либо email."
)
CLARIFY_CONTACT_TIME = (
    "Не удалось распознать удобное время. Напишите, например: завтра утром, "
    "сегодня после 17:00, в воскресенье или в любое время."
)
CLARIFY_INCOMPLETE_CONTACT_TIME = (
    "Уточните, пожалуйста, время. Например: 13:30 или 14:00."
)
LEAD_CREATED = "Заявка оформлена."


@dataclass(frozen=True, slots=True)
class LeadDialogueState:
    active: bool
    service: str | None
    problem: str | None
    city: str | None
    name: str | None
    phone: str | None
    email: str | None
    preferred_contact_time: str | None
    expected_step: str | None
    price_requested: bool
    price_answered: bool
    booking_offered: bool
    booking_confirmed: bool
    booking_declined: bool


def process_lead_dialogue(
    db: Session,
    session_id: str,
    messages: Sequence[DialogueMessage],
) -> str | None:
    existing_lead = get_lead_by_session_id(db, session_id)
    if existing_lead is not None:
        return None

    cycle = _current_dialogue_cycle(messages)
    if not cycle:
        return None

    state = _build_state(cycle)
    if not state.active:
        return None

    latest_user_message = next(
        (
            message.content.strip()
            for message in reversed(cycle)
            if message.role == "user"
        ),
        "",
    )

    if not state.service:
        return CLARIFY_TASK if state.expected_step == "task" else ASK_TASK

    if (
        state.price_requested
        and not state.price_answered
        and state.service in PRICE_PROMPTS
        and state.service != "ремонт кондиционера"
    ):
        return PRICE_PROMPTS[state.service]

    if state.service == "ремонт кондиционера" and not state.problem:
        if state.expected_step == "problem":
            return CLARIFY_PROBLEM
        return REPAIR_PRICE_AND_PROBLEM if state.price_requested else ASK_PROBLEM

    if not state.city:
        if state.problem:
            return _problem_help_response(state.problem)
        if state.service in PRICE_PROMPTS:
            return PRICE_PROMPTS[state.service]
        return CLARIFY_CITY if state.expected_step == "city" else ASK_CITY

    if state.booking_declined:
        return BOOKING_DECLINED

    if not state.booking_offered:
        return f"Отлично, {state.city} входит в нашу зону обслуживания. {OFFER_BOOKING}"

    if not state.booking_confirmed:
        if state.expected_step == "booking":
            return None
        return OFFER_BOOKING

    if not state.name:
        return CLARIFY_NAME if state.expected_step == "name" else ASK_NAME

    if not (state.phone or state.email):
        return CLARIFY_CONTACT if state.expected_step == "contact" else ASK_CONTACT

    if not state.preferred_contact_time:
        if (
            state.expected_step == "contact_time"
            and is_incomplete_contact_time(latest_user_message)
        ):
            return CLARIFY_INCOMPLETE_CONTACT_TIME
        return (
            CLARIFY_CONTACT_TIME
            if state.expected_step == "contact_time"
            else ASK_CONTACT_TIME
        )

    details = (
        f"Услуга: {state.service}. "
        f"Проблема: {state.problem or latest_user_message}. "
        f"Город: {state.city}."
    )
    lead = create_or_update_lead(
        db=db,
        session_id=session_id,
        name=state.name,
        phone=state.phone,
        email=state.email,
        details=details,
        preferred_contact_time=state.preferred_contact_time,
    )
    return format_lead_confirmation(lead)


def _current_dialogue_cycle(
    messages: Sequence[DialogueMessage],
) -> list[DialogueMessage]:
    normalized_messages = [
        (
            message,
            normalize_air_conditioner_text(message.content),
        )
        for message in messages
    ]
    last_completion_index = max(
        (
            index
            for index, (message, _) in enumerate(normalized_messages)
            if message.role == "assistant"
            and (
                LEAD_CREATED in message.content
                or message.content == BOOKING_DECLINED
            )
        ),
        default=-1,
    )
    start_index = max(
        (
            index
            for index, (message, normalized_content) in enumerate(normalized_messages)
            if index > last_completion_index
            and message.role == "user"
            and LEAD_INTENT_PATTERN.search(normalized_content)
        ),
        default=-1,
    )
    if start_index == -1:
        return []
    return list(messages[start_index:])


def _build_state(messages: Sequence[DialogueMessage]) -> LeadDialogueState:
    user_messages = [
        message.content.strip()
        for message in messages
        if message.role == "user" and message.content.strip()
    ]
    extracted = extract_lead_data(user_messages)
    service = (
        extracted.service
        if extracted.service and extracted.service != "консультация"
        else None
    )
    problem = _find_problem(user_messages)
    city = _find_city(user_messages)
    name = extracted.name
    phone = extracted.phone
    email = extracted.email
    preferred_contact_time = extracted.preferred_contact_time
    expected_step: str | None = None
    booking_offered = False
    booking_confirmed = False
    booking_declined = False

    for index, message in enumerate(messages):
        if message.role != "assistant":
            continue

        step = _step_for_prompt(message.content)
        if step is None:
            continue

        expected_step = step
        if step == "booking":
            booking_offered = True
        answer = _next_user_message(messages, index + 1)
        if answer is None:
            continue

        if step == "task":
            parsed_service = extract_service(answer)
            if parsed_service and parsed_service != "консультация":
                service = parsed_service
                expected_step = None
        elif step == "problem":
            parsed_problem = _extract_problem(answer)
            if parsed_problem:
                problem = parsed_problem
                expected_step = None
        elif step == "city":
            parsed_city = _extract_city(answer)
            if parsed_city:
                city = parsed_city
                expected_step = None
        elif step == "name":
            parsed_name = _parse_name_answer(answer)
            if parsed_name:
                name = parsed_name
                expected_step = None
        elif step == "contact":
            phone = phone or extract_phone(answer)
            email = email or extract_email(answer)
            if phone or email:
                expected_step = None
        elif step == "contact_time":
            parsed_contact_time = extract_preferred_contact_time(answer)
            if parsed_contact_time:
                preferred_contact_time = parsed_contact_time
                expected_step = None
        elif step == "booking":
            if AFFIRMATIVE_PATTERN.fullmatch(answer):
                booking_confirmed = True
                expected_step = None
            elif NEGATIVE_PATTERN.fullmatch(answer):
                booking_declined = True
                expected_step = None

    return LeadDialogueState(
        active=True,
        service=service,
        problem=problem,
        city=city,
        name=name,
        phone=phone,
        email=email,
        preferred_contact_time=preferred_contact_time,
        expected_step=expected_step,
        price_requested=any(PRICE_PATTERN.search(message) for message in user_messages),
        price_answered=any(
            message.role == "assistant"
            and message.content in PRICE_PROMPTS.values()
            for message in messages
        ),
        booking_offered=booking_offered,
        booking_confirmed=booking_confirmed,
        booking_declined=booking_declined,
    )


def _step_for_prompt(content: str) -> str | None:
    if content == OFFER_BOOKING or content.endswith(OFFER_BOOKING):
        return "booking"

    prompts = {
        ASK_TASK: "task",
        CLARIFY_TASK: "task",
        ASK_PROBLEM: "problem",
        REPAIR_PRICE_AND_PROBLEM: "problem",
        DIAGNOSTICS_PRICE_AND_CITY: "city",
        CLEANING_PRICE_AND_CITY: "city",
        GAS_PRICE_AND_CITY: "city",
        INSTALLATION_PRICE_AND_CITY: "city",
        DISMANTLING_PRICE_AND_CITY: "city",
        CLARIFY_PROBLEM: "problem",
        ASK_CITY: "city",
        CLARIFY_CITY: "city",
        ASK_NAME: "name",
        CLARIFY_NAME: "name",
        ASK_CONTACT: "contact",
        CLARIFY_CONTACT: "contact",
        ASK_CONTACT_TIME: "contact_time",
        CLARIFY_CONTACT_TIME: "contact_time",
        CLARIFY_INCOMPLETE_CONTACT_TIME: "contact_time",
    }
    return prompts.get(content)


def _problem_help_response(problem: str) -> str:
    normalized_problem = normalize_air_conditioner_text(problem)
    if re.search(r"течет|капает", normalized_problem):
        return (
            "Понял. Течь часто связана с засором дренажа или загрязнением "
            "внутреннего блока. Устранение обычно стоит примерно 250–450 ₪, "
            "но точную стоимость можно узнать после консультации со специалистом "
            "или проверки мастером. Цена зависит от причины, модели кондиционера "
            "и сложности доступа. Подскажите, пожалуйста, в каком городе "
            "находится кондиционер?"
        )
    if re.search(r"не\s+охлаждает|слабо\s+дует|обмерз|лед", normalized_problem):
        return (
            "Понял. Причиной могут быть загрязнение, недостаток газа, датчик "
            "или внешний блок. Ремонт обычно начинается примерно от 250 ₪, "
            "но точную стоимость можно узнать после консультации со специалистом "
            "или проверки мастером. Цена зависит от причины, модели кондиционера "
            "и сложности доступа. Подскажите, пожалуйста, в каком городе "
            "находится кондиционер?"
        )
    if re.search(r"шумит|вибрирует", normalized_problem):
        return (
            "Понял. Шум часто связан с загрязнением вентилятора, креплением "
            "или износом деталей. Точную стоимость можно узнать после проверки "
            "специалистом: она зависит от причины, модели кондиционера и "
            "сложности доступа. Подскажите, пожалуйста, в каком городе "
            "находится кондиционер?"
        )
    if re.search(r"не\s+включается|выбивает|ошибк", normalized_problem):
        return (
            "Понял. Если кондиционер вообще не включается, лучше не пытаться "
            "запускать его повторно до проверки: причина может быть в питании, "
            "плате управления, пульте или компрессоре. Диагностика обычно стоит "
            "150–250 ₪, но точную стоимость ремонта можно узнать только после "
            "консультации со специалистом или проверки мастером. Цена зависит "
            "от причины поломки, модели кондиционера и сложности доступа. "
            "Подскажите, пожалуйста, в каком городе находится кондиционер?"
        )
    return (
        "Понял задачу. Для точной оценки важно учитывать модель, доступ "
        f"и состояние оборудования. {ASK_CITY}"
    )


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


def _find_problem(messages: Sequence[str]) -> str | None:
    for message in reversed(messages):
        problem = _extract_problem(message)
        if problem:
            return problem
    return None


def _extract_problem(text: str) -> str | None:
    normalized_text = normalize_air_conditioner_text(text)
    if PROBLEM_PATTERN.search(normalized_text):
        return text.strip()
    return None


def _find_city(messages: Sequence[str]) -> str | None:
    for message in reversed(messages):
        city = _extract_city(message)
        if city:
            return city
    return None


def _extract_city(text: str) -> str | None:
    normalized_text = normalize_air_conditioner_text(text)
    for alias, city in CITY_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", normalized_text):
            return city
    return None


def _parse_name_answer(text: str) -> str | None:
    candidate = text.strip()
    if not SIMPLE_NAME_PATTERN.fullmatch(candidate):
        return None
    if _extract_city(candidate):
        return None
    return " ".join(part.capitalize() for part in candidate.split())
