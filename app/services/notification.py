# Этот файл отправляет владельцу компании email со сводкой новой заявки.

from email.message import EmailMessage
import logging
import smtplib

from app.config import settings
from app.models.lead import Lead


logger = logging.getLogger(__name__)


def send_lead_notification(lead: Lead) -> bool:
    if not all(
        (
            settings.smtp_host,
            settings.email_from,
            settings.email_to,
        )
    ):
        logger.info("SMTP-уведомление пропущено: настройки email не заполнены")
        return False

    message = EmailMessage()
    message["Subject"] = f"Новая заявка #{lead.id}"
    message["From"] = settings.email_from
    message["To"] = settings.email_to
    message.set_content(format_lead_email(lead))

    try:
        with smtplib.SMTP(
            settings.smtp_host,
            settings.smtp_port,
            timeout=15,
        ) as smtp:
            if settings.smtp_use_tls:
                smtp.starttls()
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException):
        logger.exception("Не удалось отправить email по новой заявке")
        return False

    return True


def format_lead_email(lead: Lead) -> str:
    contact = lead.phone or lead.email or "не указан"
    return "\n".join(
        (
            f"Заявка: #{lead.id}",
            f"Имя: {lead.name or 'не указано'}",
            f"Контакт: {contact}",
            f"Удобное время: {lead.preferred_contact_time or 'не указано'}",
            f"Описание: {lead.message or 'не указано'}",
            f"Статус: {lead.status}",
        )
    )
