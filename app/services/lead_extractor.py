# Этот файл извлекает контактные данные и интересующую услугу из сообщений пользователя.

from collections.abc import Iterable
from dataclasses import dataclass
import re


EMAIL_PATTERN = re.compile(
    r"(?<![\w.+-])[\w.+-]+@[\w-]+(?:\.[\w-]+)+(?![\w.-])",
    re.IGNORECASE,
)
PHONE_PATTERN = re.compile(
    r"(?<!\d)(?:\+7|8|7)?[\s(.-]*(?:\d[\s()\-]*){10}(?!\d)"
)
NAME_PATTERNS = (
    re.compile(
        r"(?:меня\s+зовут|мо[её]\s+имя|имя)\s*[:\-]?\s*"
        r"([А-ЯЁA-Z][а-яёa-z]+(?:[\s-][А-ЯЁA-Z][а-яёa-z]+){0,2})",
        re.IGNORECASE,
    ),
    re.compile(
        r"^\s*([А-ЯЁA-Z][а-яёa-z]{1,30})"
        r"(?=\s*[,;:]?\s*(?:\+7|8|7)?[\s(.-]*(?:\d[\s()\-]*){10})",
        re.IGNORECASE,
    ),
)
SERVICE_KEYWORDS = {
    "выездная диагностика": (
        "диагност",
        "осмотр",
        "выезд мастера",
    ),
    "мелкий ремонт": (
        "ремонт",
        "почин",
        "фурнитур",
        "двер",
    ),
    "сборка мебели": (
        "сборк",
        "мебел",
        "шкаф",
        "стол",
    ),
    "установка оборудования": (
        "установ",
        "монтаж",
        "подключ",
        "полк",
        "карниз",
    ),
    "техническое обслуживание": (
        "обслужив",
        "техобслуж",
        "планов",
    ),
    "консультация": (
        "консультац",
        "проконсульт",
        "вопрос специалист",
    ),
}


@dataclass(frozen=True, slots=True)
class ExtractedLead:
    name: str | None
    phone: str | None
    email: str | None
    service: str | None


def extract_lead_data(messages: Iterable[str]) -> ExtractedLead:
    texts = [message.strip() for message in messages if message.strip()]
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    service: str | None = None

    for text in reversed(texts):
        if name is None:
            name = _extract_name(text)
        if phone is None:
            phone_match = PHONE_PATTERN.search(text)
            if phone_match:
                phone = _normalize_phone(phone_match.group(0))
        if email is None:
            email_match = EMAIL_PATTERN.search(text)
            if email_match:
                email = email_match.group(0).lower()
        if service is None:
            service = _extract_service(text)

    return ExtractedLead(
        name=name,
        phone=phone,
        email=email,
        service=service,
    )


def extract_name(text: str) -> str | None:
    return _extract_name(text)


def extract_phone(text: str) -> str | None:
    match = PHONE_PATTERN.search(text)
    return _normalize_phone(match.group(0)) if match else None


def extract_email(text: str) -> str | None:
    match = EMAIL_PATTERN.search(text)
    return match.group(0).lower() if match else None


def extract_service(text: str) -> str | None:
    return _extract_service(text)


def _extract_name(text: str) -> str | None:
    for pattern in NAME_PATTERNS:
        match = pattern.search(text)
        if match:
            return " ".join(part.capitalize() for part in match.group(1).split())
    return None


def _normalize_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 11 and digits[0] in {"7", "8"}:
        digits = digits[1:]
    return f"+7{digits}"


def _extract_service(text: str) -> str | None:
    normalized_text = text.casefold()
    for service, keywords in SERVICE_KEYWORDS.items():
        if any(keyword in normalized_text for keyword in keywords):
            return service
    return None
