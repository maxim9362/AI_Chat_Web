# Этот файл проверяет содержание email-уведомления о новой заявке.

import unittest

from app.models.lead import Lead
from app.services.notification import format_lead_email


class NotificationTests(unittest.TestCase):
    def test_email_contains_contact_time_and_request_details(self) -> None:
        lead = Lead(
            id=12,
            session_id="notification-test",
            name="Максим",
            phone="+972501234567",
            email=None,
            message=(
                "Услуга: ремонт кондиционера. "
                "Проблема: течет вода. Город: Ашдод."
            ),
            preferred_contact_time="завтра утром",
            status="new",
        )

        content = format_lead_email(lead)

        self.assertIn("Имя: Максим", content)
        self.assertIn("Контакт: +972501234567", content)
        self.assertIn("Удобное время: завтра утром", content)
        self.assertIn("Проблема: течет вода", content)


if __name__ == "__main__":
    unittest.main()
