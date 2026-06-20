<!-- Этот файл содержит инструкции по настройке и запуску AI-консультанта. -->

# Universal AI Site Consultant

FastAPI-приложение с Gemini, PostgreSQL, локальными embeddings,
ChromaDB, SSE-чатом и email-уведомлениями о новых заявках.

## Быстрый запуск через Docker

Требуются Docker Desktop и Gemini API key.

1. Создайте `.env` из примера:

```powershell
Copy-Item .env.example .env
```

2. Заполните минимум:

```dotenv
GEMINI_API_KEY=ваш_ключ
```

3. Запустите проект:

```powershell
docker compose up --build
```

При первом запуске приложение автоматически:

- дождется готовности PostgreSQL;
- создаст таблицы;
- загрузит локальную embedding-модель;
- проиндексирует Markdown-файлы из `knowledge`;
- запустит FastAPI на порту `8000`.

Чат: `http://localhost:8000`

Health endpoint: `http://localhost:8000/health`

Остановка:

```powershell
docker compose down
```

Данные PostgreSQL и ChromaDB сохраняются в Docker volumes
`postgres_data` и `chroma_data`.

## Настройка `.env`

Основные переменные:

```dotenv
APP_NAME=Universal AI Site Consultant
DEBUG=false

GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.5-flash
GEMINI_FALLBACK_MODEL=gemini-2.5-flash

EMBEDDING_MODEL_NAME=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
RAG_MAX_DISTANCE=0.78

SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_USE_TLS=true
EMAIL_FROM=
EMAIL_TO=
```

В Docker значение `DATABASE_URL` автоматически указывает на сервис
`postgres`. Для локального запуска используется значение из `.env`.

Если SMTP не настроен, lead все равно создается, а причина пропуска email
записывается в лог приложения.

## Таблицы PostgreSQL

В Docker таблицы создаются автоматически. Ручной запуск внутри контейнера:

```powershell
docker compose exec app python scripts/init_db.py
```

Для локального запуска:

```powershell
python scripts/init_db.py
```

## Индексация базы знаний

Markdown-файлы находятся в каталоге `knowledge`. После их изменения выполните:

```powershell
docker compose exec app python scripts/ingest_knowledge.py
```

Локальный вариант:

```powershell
python scripts/ingest_knowledge.py
```

Чтобы полностью пересоздать Docker-volume ChromaDB:

```powershell
docker compose down
docker volume rm ai_chat_web_chroma_data
docker compose up --build
```

Имя volume может отличаться, если каталог проекта переименован. Точное имя
можно узнать командой `docker volume ls`.

## Локальный запуск без Docker

Требуется Python 3.12 и запущенный PostgreSQL:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts/init_db.py
python scripts/ingest_knowledge.py
uvicorn app.main:app --reload
```

После запуска откройте `http://127.0.0.1:8000`.

## Проверка email

После заполнения SMTP-переменных:

```powershell
docker compose exec app python scripts/check_email.py
```

Или локально:

```powershell
python scripts/check_email.py
```

## Как встроить чат на WordPress

Backend AI-консультанта должен быть доступен по HTTPS на отдельном домене,
например `https://ai.example.com`.

1. Откройте WordPress admin.
2. Установите WPCode или Insert Headers and Footers.
3. Добавьте перед закрывающим тегом `body` одну строку:

```html
<script src="https://your-ai-domain.com/widget/chat-widget.js"></script>
```

4. Сохраните изменения и откройте сайт.
5. В правом нижнем углу появится кнопка «AI-консультант».

WordPress-плагин для самого чата не требуется. Виджет автоматически определяет
адрес backend из собственного `src` и отправляет запросы на
`https://your-ai-domain.com/api/chat`.

Для обычного HTML-сайта используется та же строка:

```html
<script src="https://your-ai-domain.com/widget/chat-widget.js"></script>
```

## CORS для сайта клиента

В `.env` backend необходимо перечислить разрешенные сайты через запятую:

```dotenv
ALLOWED_ORIGINS=https://client-site.co.il,https://www.client-site.co.il
```

Не используйте `*` в production. После изменения `.env` перезапустите
контейнер приложения:

```powershell
docker compose up -d --force-recreate app
```

Локальная демонстрация доступна по адресу:

`http://localhost:8000/static/widget-demo.html`

Сам JavaScript-виджет:

`http://localhost:8000/widget/chat-widget.js`
