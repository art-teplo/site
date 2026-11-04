# art-teplo.by — бэкенд

Django 6.0 + DRF + Unfold, Celery, Postgres, Redis; ASGI на uvicorn. Зависимости — [uv](https://docs.astral.sh/uv/).
Как устроено и почему — [`../docs/stack.md`](../docs/stack.md) (раздел 7) и [`../docs/decisions.md`](../docs/decisions.md) (с № 63).

## Запуск локально

Всё поднимается в Docker из `root/`, код смонтирован, Django перезапускается сам:

```bash
cd ../root
cp .env.example .env          # один раз
docker compose -f docker-compose.yaml -f docker-compose.dev.yaml up --build
docker compose -f docker-compose.yaml -f docker-compose.dev.yaml run --rm backend createsuperuser
```

- API: http://localhost:8000/api/health/, Swagger: http://localhost:8000/api/schema/swagger/
- Админка через nginx: http://localhost:8080/admin/
- Команды Django: `docker compose -f docker-compose.yaml -f docker-compose.dev.yaml run --rm backend <команда>`. В уже запущенном контейнере — `… exec -T backend python3 manage.py <команда>`: образ distroless, нет `sh` и `python`, только `python3`.

## Проверки (из `backend/`)

```bash
uv sync
uv run ruff check && uv run ruff format --check
uv run pytest                 # нужен postgres из dev-compose на localhost:5432
```

Новая модель — `docker compose -f docker-compose.yaml -f docker-compose.dev.yaml run --rm backend makemigrations` из `root/`: код смонтирован, файлы миграций появятся в `backend/src`. CI падает, если миграции забыты.

## Структура

```
src/
  manage.py
  settings/       settings.py (env с префиксом BACKEND__), asgi.py, celery.py, urls.py
  apps/core/      healthcheck, команда startservice (uvicorn); groups.py — права группы «Менеджер»
  apps/core/utils.py  AutoUploadTo, валидаторы файлов, client_ip
  apps/leads/     заявки: POST /api/leads/, админка, Celery (Telegram, чистка); команда runbot
  apps/leads/telegram/  aiogram: texts.py (все тексты), service.py (сообщение, отправка), handlers.py (кнопки, команды)
  apps/content/   настройки сайта (django-solo), вопрос-ответ, проекты, блог, шоурум: API только на чтение,
                  html.py (чистка текста статей), сигнал фронту обновить страницы; команда loaddemo
                  (заливает и каталог)
  apps/catalog/   категории, бренды (логотип SVG/PNG/WebP, «гарантия до»), сроки изготовления по сериям;
                  товары пока в коде фронта и ссылаются на них по slug. Тег кэша фронта — catalog
  tests/          pytest
```

Новое приложение — `src/apps/<name>/` с `apps.py` (`name = 'apps.<name>'`), в `INSTALLED_APPS`, URL — внутри `api/` в `settings/urls.py`.

## Контент локально

Настройки сайта (с видео шоурума), вопрос-ответ, проекты, блог и шоурум — в админке, раздел «Сайт»; категории, бренды и сроки — раздел «Каталог». Наполнить демо-записями с фронта (вместе с фото из `web/public/images`):

```bash
docker compose -f docker-compose.yaml -f docker-compose.dev.yaml run --rm backend loaddemo   # из root/
```

Повторный запуск обновляет записи и не дублирует фото. Чтобы правки сразу появлялись на `localhost:3000`, задайте одинаковый секрет в `root/.env` (`BACKEND__FRONTEND__REVALIDATE_URL=http://host.docker.internal:3000/api/revalidate`, `BACKEND__FRONTEND__REVALIDATE_SECRET`) и в `web/.env.local` (`REVALIDATE_SECRET`), см. `web/.env.example`. Без этого фронт обновит страницы сам — в течение часа.

## Доступ к админке

Менеджер — пользователь со «Статусом персонала» в группе «Менеджер»: заявки и контент, без пользователей и настроек. Права группы — в `apps/core/groups.py`, после `migrate` выставляются заново: новая модель для менеджеров — строка в `MANAGER_PERMISSIONS`. Пять неудачных входов под одним логином с одного IP — блок на час (`django-axes`), снять — `… exec -T backend python3 manage.py axes_reset_username <логин>`. Пароль — от 12 символов.

## Telegram локально

Заявки уходят в закрытую группу, кнопки «Беру» / «Отказаться» принимает сервис `telegram_bot` (long polling). Для разработки — свой тестовый бот, не боевой: один токен нельзя опрашивать из двух мест.

1. @BotFather → `/newbot`, токен — в `root/.env` (`BACKEND__TELEGRAM__BOT_TOKEN`).
2. Группа, в неё — бот и вы; в группе `/chatid`, ответ — в `BACKEND__TELEGRAM__CHAT_ID`.
3. @BotFather → Bot Settings → Allow Groups → Turn off: бота больше никуда не добавить.
4. Перезапустить compose. Без токена уведомления выключены, бот спит.

Что сделать на сервере (боевой бот, `.env`, фронт, бэкап файлов) — чек-лист в [`../docs/stack.md`](../docs/stack.md), раздел «Заявки: что сделать при переезде на прод».

Ссылки в сообщении («Открыть в админке», «Открыть товар на сайте») собираются из `BACKEND__PUBLIC_URL` и `BACKEND__SITE_URL`. Адреса `localhost` Telegram ссылками не делает — для проверки подставьте `lvh.me` (публичное имя, которое смотрит на 127.0.0.1): `http://lvh.me:8080` и `http://lvh.me:3000`, а `lvh.me` добавьте в `BACKEND__ALLOWED_HOSTS` и `BACKEND__CSRF_TRUSTED_ORIGINS`.

## Правила

- Настройки только из env (`BACKEND__…`), новая переменная — ещё в `root/.env.example` и `root/docker-compose.yaml`.
- Публичный API — только чтение (`IsAuthenticatedOrReadOnly` по умолчанию), запись открывается точечно.
- Код — ruff (одинарные кавычки, 79 символов), сообщения коммитов — как в [`../CLAUDE.md`](../CLAUDE.md).
- Вызовы и поля с несколькими аргументами — по одному на строку, с запятой в конце: ruff format сохраняет столбик, но сам его не делает, если вызов влезает в строку.
- HTTP-коды — `rest_framework.status` в ответах DRF; тексты для людей — константами (бот — `apps/leads/telegram/texts.py`).
