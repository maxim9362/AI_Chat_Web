# Этот файл создает все таблицы приложения в настроенной базе данных.

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import app.models  # noqa: E402, F401
from sqlalchemy import inspect, text  # noqa: E402
from app.config import settings  # noqa: E402
from app.database.base import Base  # noqa: E402
from app.database.db import engine  # noqa: E402
from app.models.lead import Lead  # noqa: E402


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    columns = {
        column["name"]
        for column in inspect(engine).get_columns("leads")
    }
    if "preferred_contact_time" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE leads ADD COLUMN "
                    "preferred_contact_time VARCHAR(255)"
                )
            )
    lead_session_index = next(
        index
        for index in Lead.__table__.indexes
        if index.name == "uq_leads_session_id"
    )
    lead_session_index.create(bind=engine, checkfirst=True)
    print(f"Таблицы созданы: {', '.join(sorted(Base.metadata.tables))}")
    print(f"Подключение: {engine.url.render_as_string(hide_password=True)}")


if __name__ == "__main__":
    init_db()
