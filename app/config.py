# Этот файл загружает настройки приложения из переменных окружения и файла .env.

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    app_name: str = "Universal AI Site Consultant"
    debug: bool = False

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/ai_consultant"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash"
    gemini_fallback_model: str = "gemini-2.5-flash"
    embedding_model_name: str = (
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )

    knowledge_dir: Path = PROJECT_ROOT / "knowledge"
    chroma_path: Path = PROJECT_ROOT / "chroma_data"
    chroma_collection: str = "business_knowledge"
    rag_max_distance: float = 0.78
    allowed_origins: str = (
        "http://localhost:8000,http://127.0.0.1:8000"
    )

    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    email_from: str = ""
    email_to: str = ""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("knowledge_dir", "chroma_path", mode="after")
    @classmethod
    def resolve_project_path(cls, value: Path) -> Path:
        if value.is_absolute():
            return value
        return PROJECT_ROOT / value

    @property
    def allowed_origin_list(self) -> list[str]:
        return [
            origin.strip().rstrip("/")
            for origin in self.allowed_origins.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
