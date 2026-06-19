# Этот файл формирует локальные ответы на приветствия и неопределенные реплики.

import re


GREETING_PATTERN = re.compile(
    r"^(?:привет|здравствуйте|здравствуй|добрый\s+(?:день|вечер|утро)|"
    r"хай|hello|hi)[!,.?\s]*$",
    re.IGNORECASE,
)
THANKS_PATTERN = re.compile(
    r"^(?:спасибо|благодарю|понятно|ясно|хорошо|ок|окей)[!,.?\s]*$",
    re.IGNORECASE,
)
FAREWELL_PATTERN = re.compile(
    r"^(?:пока|до\s+свидания|до\s+встречи|всего\s+доброго)[!,.?\s]*$",
    re.IGNORECASE,
)
VAGUE_PATTERN = re.compile(
    r"^(?:что|как|помоги|помощь|расскажи|можно\s+подробнее|"
    r"не\s+понял(?:а)?)[!,.?\s]*$",
    re.IGNORECASE,
)
STATUS_PATTERN = re.compile(
    r"\b(?:статус|что\s+с\s+(?:моей\s+)?заявк\w*|"
    r"заявк\w*\s+(?:принята|оформлена))\b",
    re.IGNORECASE,
)


def is_silent_post_lead_message(message: str) -> bool:
    normalized_message = " ".join(message.split())
    return bool(
        THANKS_PATTERN.fullmatch(normalized_message)
        or FAREWELL_PATTERN.fullmatch(normalized_message)
    )


def get_conversation_response(
    message: str,
    lead_created: bool = False,
    customer_name: str | None = None,
    lead_status: str | None = None,
) -> str | None:
    normalized_message = " ".join(message.split())
    greeting_name = f", {customer_name}" if customer_name else ""

    if lead_created and STATUS_PATTERN.search(normalized_message):
        if lead_status == "new":
            return (
                "Ваша заявка принята и ожидает обработки менеджером. "
                "Повторно оставлять данные не нужно."
            )
        return (
            f"Текущий статус вашей заявки: {lead_status or 'принята'}. "
            "Повторно оставлять данные не нужно."
        )

    if GREETING_PATTERN.fullmatch(normalized_message):
        if lead_created:
            return (
                f"Здравствуйте{greeting_name}! Ваша заявка уже оформлена. "
                "Чем еще могу помочь?"
            )
        return (
            "Здравствуйте! Я могу рассказать об услугах, ценах, графике работы, "
            "контактах или помочь оформить заявку."
        )

    if THANKS_PATTERN.fullmatch(normalized_message):
        return "Пожалуйста! Задайте еще один вопрос, если потребуется помощь."

    if FAREWELL_PATTERN.fullmatch(normalized_message):
        if lead_created:
            return None
        return "До свидания! Будем рады помочь снова."

    if VAGUE_PATTERN.fullmatch(normalized_message):
        if lead_created:
            return (
                "Уточните, пожалуйста, что именно вы хотите узнать по уже "
                "оформленной заявке или по обслуживанию кондиционера."
            )
        return (
            "Пожалуйста, уточните вопрос. Например, спросите об услугах, "
            "стоимости, графике работы, контактах или оформлении заявки."
        )

    return None
