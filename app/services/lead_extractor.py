# Этот файл извлекает контактные данные и интересующую услугу из сообщений пользователя.

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
import re
from zoneinfo import ZoneInfo


EMAIL_PATTERN = re.compile(
    r"(?<![\w.+-])[\w.+-]+@[\w-]+(?:\.[\w-]+)+(?![\w.-])",
    re.IGNORECASE,
)
PHONE_CANDIDATE_PATTERN = re.compile(
    r"(?<!\d)(?:\+972|00972|0)?[\s(.-]*(?:\d[\s()\-]*){8,10}(?!\d)"
)
NAME_PATTERNS = (
    re.compile(
        r"(?:меня\s+зовут|мо[её]\s+имя|имя)\s*[:\-]?\s*"
        r"([А-ЯЁA-Z][а-яёa-z]+(?:[\s-][А-ЯЁA-Z][а-яёa-z]+){0,2})",
        re.IGNORECASE,
    ),
    re.compile(
        r"^\s*([А-ЯЁA-Z][а-яёa-z]{1,30})"
        r"(?=\s*[,;:]?\s*(?:\+972|00972|0)?[\s(.-]*(?:\d[\s()\-]*){8,10})",
        re.IGNORECASE,
    ),
)
STANDALONE_NAME_PATTERN = re.compile(
    r"^[А-ЯЁA-Z][а-яёa-z]{1,30}$",
    re.IGNORECASE,
)
NON_NAME_WORDS = {
    "да",
    "нет",
    "хорошо",
    "ладно",
    "ок",
    "окей",
    "можно",
    "хочу",
    "утром",
    "вечером",
    "сегодня",
    "завтра",
    "воскресенье",
    "понедельник",
    "вторник",
    "среда",
    "четверг",
    "пятница",
    "суббота",
    "привет",
    "здравствуйте",
    "спасибо",
    "помогите",
    "консультация",
    "ремонт",
    "диагностика",
    "установка",
    "сборка",
    "ашдод",
    "ашкелон",
    "явне",
    "ган-явне",
    "кирьят-малахи",
}
SERVICE_KEYWORDS = {
    "диагностика кондиционера": (
        "диагност",
        "осмотр",
        "выезд мастера",
    ),
    "ремонт кондиционера": (
        "ремонт",
        "почин",
        "не охлаждает",
        "не греет",
        "не включается",
        "течет",
        "течёт",
        "шумит",
        "ошибка",
    ),
    "установка кондиционера": (
        "установ",
        "монтаж",
        "поставить кондиционер",
    ),
    "чистка кондиционера": (
        "чистк",
        "мойк",
        "плесень",
        "запах",
    ),
    "заправка газа": (
        "заправ",
        "газ",
        "фреон",
        "хладагент",
    ),
    "обслуживание кондиционера": (
        "обслужив",
        "техобслуж",
        "планов",
    ),
    "демонтаж кондиционера": (
        "демонтаж",
        "снять кондиционер",
        "перенести кондиционер",
    ),
    "консультация": (
        "консультац",
        "проконсульт",
        "вопрос специалист",
    ),
}
ISRAEL_TIMEZONE = ZoneInfo("Asia/Jerusalem")
TIME_PART = r"(?:[01]?\d|2[0-3])(?:[:.-][0-5]\d)"
HOUR_PART = r"(?:[01]?\d|2[0-3])"
INCOMPLETE_TIME_PATTERN = re.compile(
    r"^\s*(?:[01]?\d|2[0-3])[:.-]\d\s*$"
)
BARE_TIME_PATTERN = re.compile(
    rf"^\s*(?P<hour>[01]?\d|2[0-3])[:.-](?P<minute>[0-5]\d)\s*$"
)
CONTACT_TIME_PATTERNS = (
    re.compile(
        r"\b(?:сегодня|завтра)(?:\s+(?:утром|днем|днём|вечером|"
        rf"(?:в|после|до)\s+{TIME_PART}))?\b",
        re.IGNORECASE,
    ),
    re.compile(
        rf"\bс\s+{HOUR_PART}(?:[:.-][0-5]\d)?\s+до\s+"
        rf"{HOUR_PART}(?:[:.-][0-5]\d)?\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:утром|вечером|после\s+обеда|в\s+любое\s+время|"
        r"в\s+рабочее\s+время|после\s+работы)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:в|во)\s+(?:воскресенье|понедельник|вторник|среду|"
        r"четверг|пятницу|субботу)(?:\s+(?:утром|вечером|"
        rf"(?:в|после|до)\s+{TIME_PART}))?\b",
        re.IGNORECASE,
    ),
    re.compile(
        rf"\b(?:после|до|к|в)\s+{TIME_PART}\b",
        re.IGNORECASE,
    ),
)


@dataclass(frozen=True, slots=True)
class ExtractedLead:
    name: str | None
    phone: str | None
    email: str | None
    service: str | None
    preferred_contact_time: str | None


def extract_lead_data(messages: Iterable[str]) -> ExtractedLead:
    texts = [message.strip() for message in messages if message.strip()]
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    service: str | None = None
    preferred_contact_time: str | None = None

    for text in reversed(texts):
        if name is None:
            name = _extract_name(text) or _extract_standalone_name(text)
        if phone is None:
            phone = extract_phone(text)
        if email is None:
            email_match = EMAIL_PATTERN.search(text)
            if email_match:
                email = email_match.group(0).lower()
        if service is None:
            service = _extract_service(text)
        if preferred_contact_time is None:
            preferred_contact_time = extract_preferred_contact_time(text)

    return ExtractedLead(
        name=name,
        phone=phone,
        email=email,
        service=service,
        preferred_contact_time=preferred_contact_time,
    )


def extract_name(text: str) -> str | None:
    return _extract_name(text)


def extract_phone(text: str) -> str | None:
    for match in PHONE_CANDIDATE_PATTERN.finditer(text):
        normalized_phone = _normalize_phone(match.group(0))
        if normalized_phone is not None:
            return normalized_phone
    return None


def extract_email(text: str) -> str | None:
    match = EMAIL_PATTERN.search(text)
    return match.group(0).lower() if match else None


def extract_service(text: str) -> str | None:
    return _extract_service(text)


def extract_preferred_contact_time(
    text: str,
    moment: datetime | None = None,
) -> str | None:
    normalized_text = " ".join(text.strip().split())
    bare_time_match = BARE_TIME_PATTERN.fullmatch(normalized_text)
    if bare_time_match:
        hour = int(bare_time_match.group("hour"))
        minute = int(bare_time_match.group("minute"))
        current = _israel_datetime(moment)
        day = (
            "сегодня"
            if (hour, minute) >= (current.hour, current.minute)
            else "завтра"
        )
        return f"{day} в {hour:02d}:{minute:02d}"

    for pattern in CONTACT_TIME_PATTERNS:
        match = pattern.search(normalized_text)
        if match:
            return _normalize_time_separators(match.group(0))
    return None


def is_incomplete_contact_time(text: str) -> bool:
    return bool(INCOMPLETE_TIME_PATTERN.fullmatch(text))


def _israel_datetime(moment: datetime | None) -> datetime:
    current = moment or datetime.now(ISRAEL_TIMEZONE)
    if current.tzinfo is None:
        return current.replace(tzinfo=ISRAEL_TIMEZONE)
    return current.astimezone(ISRAEL_TIMEZONE)


def _normalize_time_separators(text: str) -> str:
    return re.sub(
        r"(?P<hour>\b(?:[01]?\d|2[0-3]))[.-](?P<minute>[0-5]\d\b)",
        r"\g<hour>:\g<minute>",
        text,
    )


def _extract_name(text: str) -> str | None:
    for pattern in NAME_PATTERNS:
        match = pattern.search(text)
        if match:
            return " ".join(part.capitalize() for part in match.group(1).split())
    return None


def _extract_standalone_name(text: str) -> str | None:
    normalized_text = text.strip()
    if not STANDALONE_NAME_PATTERN.fullmatch(normalized_text):
        return None
    if normalized_text.casefold() in NON_NAME_WORDS:
        return None
    return normalized_text.capitalize()


def _normalize_phone(phone: str) -> str | None:
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("00972"):
        digits = digits[2:]
    if digits.startswith("972"):
        national_number = digits[3:]
    elif digits.startswith("0"):
        national_number = digits[1:]
    else:
        return None

    if not re.fullmatch(r"5[0-58]\d{7}", national_number):
        return None
    return f"+972{national_number}"


def _extract_service(text: str) -> str | None:
    normalized_text = normalize_air_conditioner_text(text)
    for service, keywords in SERVICE_KEYWORDS.items():
        if any(keyword in normalized_text for keyword in keywords):
            return service
    return None


def normalize_air_conditioner_text(text: str) -> str:
    normalized_text = text.casefold().replace("ё", "е")
    conditioner_pattern = re.compile(
        r"\b(?:кондиционер\w*|кондеционер\w*|кондицеонер\w*|"
        r"кондец(?:ионер\w*)?|кондер\w*|кондей\w*|кондишен\w*)\b",
        re.IGNORECASE,
    )
    return conditioner_pattern.sub("кондиционер", normalized_text)
