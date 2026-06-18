# Этот файл описывает формат лида в ответах API.

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LeadResponse(BaseModel):
    id: int
    session_id: str
    name: str | None
    phone: str | None
    email: str | None
    message: str | None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
