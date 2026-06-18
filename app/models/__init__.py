# Этот файл импортирует все модели для регистрации их таблиц в metadata SQLAlchemy.

from app.models.lead import Lead
from app.models.message import Message
from app.models.session import Session


__all__ = ["Lead", "Message", "Session"]
