# art-teplo.by — бэкенд

Django 6.0 + DRF + Unfold, Celery, Postgres, Redis; ASGI на uvicorn. Зависимости — [uv](https://docs.astral.sh/uv/).
Как устроено и почему — [`../docs/stack.md`](../docs/stack.md) (раздел 7) и [`../docs/decisions.md`](../docs/decisions.md) (№ 63–74).

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
- Команды Django: `docker compose -f docker-compose.yaml -f docker-compose.dev.yaml run --rm backend <команда>` (в образе нет shell)

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
  apps/core/      healthcheck, команда startservice (uvicorn)
  tests/          pytest
```

Новое приложение — `src/apps/<name>/` с `apps.py` (`name = 'apps.<name>'`), в `INSTALLED_APPS`, URL — внутри `api/` в `settings/urls.py`.

## Правила

- Настройки только из env (`BACKEND__…`), новая переменная — ещё в `root/.env.example` и `root/docker-compose.yaml`.
- Публичный API — только чтение (`IsAuthenticatedOrReadOnly` по умолчанию), запись открывается точечно.
- Код — ruff (одинарные кавычки, 79 символов), сообщения коммитов — как в [`../CLAUDE.md`](../CLAUDE.md).
