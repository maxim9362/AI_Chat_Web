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
UVICORN_WORKERS=1

GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.5-flash
GEMINI_FALLBACK_MODEL=gemini-2.5-flash

EMBEDDING_MODEL_NAME=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
RAG_MAX_DISTANCE=0.78

ADMIN_USERNAME=admin
ADMIN_PASSWORD=change_me
ADMIN_SESSION_SECRET=change_me_long_random_string
ADMIN_COOKIE_SECURE=false

SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_USE_TLS=true
EMAIL_FROM=
EMAIL_TO=
```

`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` и `EMAIL_FROM` относятся
к технической почте системы. Их один раз настраивает владелец системы.
Клиенту SMTP-доступы не нужны и не передаются.

Для подключения клиента нужно изменить только `EMAIL_TO` - указать адрес,
куда этому клиенту должны приходить новые заявки.

В Docker значение `DATABASE_URL` автоматически указывает на сервис
`postgres`. Для локального запуска используется значение из `.env`.

Если SMTP не настроен или письмо не удалось отправить, лид все равно
сохраняется в PostgreSQL, приложение не падает, а причина ошибки записывается
в лог.

## Доступ к админке

Клиенту передается одна ссылка:

`https://ваш-домен/admin`

Локально админка доступна по адресу:

`http://localhost:8000/admin`

Если пользователь не вошел, `/admin` перенаправит на `/admin/login`. После
входа эта же ссылка открывает список заявок `/admin/leads`.

Первичные данные берутся из `.env`:

```dotenv
ADMIN_USERNAME=admin
ADMIN_PASSWORD=change_me
ADMIN_SESSION_SECRET=длинная_случайная_строка
ADMIN_COOKIE_SECURE=false
```

`ADMIN_USERNAME` и `ADMIN_PASSWORD` используются только при первом создании
таблицы `admin_credentials`. После этого логин и хеш пароля хранятся в
PostgreSQL, а изменения этих двух переменных в `.env` не перезаписывают
существующий доступ.

После первого входа откройте `/admin/settings` и измените стандартный пароль.
Для смены логина или пароля требуется текущий пароль. После смены пароля
администратор выходит из системы и входит заново.

`ADMIN_SESSION_SECRET` подписывает cookie-сессию и не должен передаваться
клиенту или публиковаться. Для production по HTTPS установите
`ADMIN_COOKIE_SECURE=true`.

Проект не является SaaS: учетная запись относится только к одной установке
одного клиента.

## Работа с заявками

В `/admin/leads` доступны:

- список заявок от новых к старым;
- карточка заявки и последние сообщения диалога;
  - изменение статуса `new`, `in_progress`, `done`, `cancelled`;
  - ссылки для звонка и WhatsApp;
  - полное удаление заявки с подтверждением.
  
  Удаление выполняется только через защищенный POST-запрос. Вместе с заявкой
  из PostgreSQL удаляются сообщения и сессия соответствующего диалога.

  Заявки автоматически хранятся 14 дней. После истечения срока приложение
  удаляет заявку, ее сообщения и сессию. Очистка запускается при старте
  приложения и затем каждый час. Срок можно изменить в `.env`:

  ```dotenv
  LEAD_RETENTION_DAYS=14
  ```

## Браузерные уведомления в админке

1. Откройте `/admin` и войдите.
2. Перейдите в список заявок.
3. Нажмите «Включить уведомления».
4. Разрешите уведомления в браузере.

Страница проверяет новые заявки каждые 12 секунд. Уведомления работают только
пока `/admin/leads` открыта. Service Worker, Push API и внешние сервисы не
используются. Если Notification API недоступен или запрещен, админка
продолжает работать.

Email-уведомления остаются необязательными: основной способ просмотра заявок
— `/admin`.

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
python scripts/ingest_knowledge.py
uvicorn app.main:app --reload
```
  
  При запуске FastAPI таблицы и первый администратор создаются автоматически.
  Отдельно запускать `scripts/init_db.py` для админки не требуется.

  После запуска одновременно доступны:

  - чат: `http://127.0.0.1:8000`;
  - админка: `http://127.0.0.1:8000/admin`.

## Проверка email

После настройки технического SMTP и заполнения `EMAIL_TO`:

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

## Архитектура состояния

Проект устанавливается отдельно для каждого бизнеса: одна установка, один
PostgreSQL и одна ChromaDB. Мультиклиентность, `tenant_id` и `client_id` не
используются.

Посетители сайта разделяются по `session_id`, который создается frontend или
widget и хранится в `localStorage` браузера. Backend использует его только как
ключ для загрузки данных из PostgreSQL.

FastAPI не хранит историю, состояние заявки или шаг диалога в памяти между
запросами. При каждом сообщении backend:

1. находит или создает сессию в PostgreSQL;
2. сохраняет сообщение пользователя;
3. загружает историю этой сессии;
4. проверяет наличие лида в PostgreSQL;
5. восстанавливает `lead_state` из истории и лида;
6. сохраняет ответ консультанта обратно в PostgreSQL.

Поэтому перезапуск приложения не очищает диалог, а разные worker-процессы
видят одинаковое состояние. Для запуска нескольких workers укажите, например:

```dotenv
UVICORN_WORKERS=2
```

После изменения пересоздайте контейнер приложения:

```powershell
docker compose up -d --force-recreate app
```

ChromaDB содержит только индекс Markdown-файлов базы знаний. История
посетителей, контакты и заявки в ChromaDB не записываются.
