<!-- Этот файл содержит инструкции по настройке и запуску AI-консультанта. -->

# Universal AI Site Consultant

FastAPI-приложение с потоковым Gemini-чатом, PostgreSQL, локальным RAG и
ChromaDB. Факты о компании загружаются из Markdown-файлов в каталоге
`knowledge`.

## Требования

- Python 3.12
- Docker
- Gemini API key

## Установка

Создайте виртуальное окружение и установите зависимости:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Создайте `.env` на основе `.env.example` и укажите `GEMINI_API_KEY`.

## PostgreSQL

Запустите базу данных и создайте таблицы:

```powershell
docker compose up -d postgres
python scripts/init_db.py
```

## База знаний

Markdown-файлы размещаются в подпапках каталога `knowledge`. Для построения
индекса выполните:

```powershell
python scripts/ingest_knowledge.py
```

При первом запуске embedding-модель из `EMBEDDING_MODEL_NAME` будет загружена
локально. После загрузки векторизация выполняется на компьютере без API-ключа.
После изменения Markdown-файлов команду индексации нужно выполнить повторно.

## Запуск

```powershell
uvicorn app.main:app --reload
```

Интерфейс будет доступен по адресу `http://127.0.0.1:8000`.

## Поведение RAG

Для каждого вопроса приложение выполняет поиск в ChromaDB и передает Gemini до
пяти релевантных фрагментов. Если подходящих данных нет, чат отвечает:

> По этому вопросу лучше связаться со специалистом компании.
