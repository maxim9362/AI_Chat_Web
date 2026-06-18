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
CONSULTATION_PATTERN = re.compile(
    r"(?:нужна|нужен|хочу|требуется|интересует)\s+"
    r"(?:консультац\w*|помощ\w*\s+специалист\w*)",
    re.IGNORECASE,
)


def get_conversation_response(message: str) -> str | None:
    normalized_message = " ".join(message.split())

    if CONSULTATION_PATTERN.search(normalized_message):
        return (
            "Здравствуйте! Опишите, пожалуйста, вашу задачу. "
            "Для оформления заявки также можно оставить имя и телефон или email."
        )

    if GREETING_PATTERN.fullmatch(normalized_message):
        return (
            "Здравствуйте! Я могу рассказать об услугах, ценах, графике работы, "
            "контактах или помочь оформить заявку."
        )

    if THANKS_PATTERN.fullmatch(normalized_message):
        return "Пожалуйста! Задайте еще один вопрос, если потребуется помощь."

    if FAREWELL_PATTERN.fullmatch(normalized_message):
        return "До свидания! Будем рады помочь снова."

    if VAGUE_PATTERN.fullmatch(normalized_message):
        return (
            "Пожалуйста, уточните вопрос. Например, спросите об услугах, "
            "стоимости, графике работы, контактах или оформлении заявки."
        )

    return None
