# Заявки и Telegram — план

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** заявка с сайта сохраняется на бэке, приходит в группу Telegram, менеджеры берут её кнопкой.

**Architecture:** приложение `apps/leads` (модель, API, админка, задачи Celery) + пакет `apps/leads/telegram` (HTTP-клиент Bot API, тексты и кнопки, обработка обновлений) + команда `runbot` (long polling) отдельным сервисом compose.

**Tech Stack:** Django 6.0, DRF, Celery, httpx, Unfold; Next.js 16 (клиентский `fetch`).

**Spec:** `docs/superpowers/specs/2026-11-04-leads-telegram-design.md`

## Global Constraints

- Код бэка — ruff (одинарные кавычки, 79 символов); настройки только из env `BACKEND__…`, новая переменная — в `root/.env.example` и `root/docker-compose.yaml`.
- Файл заявки ≤ 50 000 000 байт (лимит Bot API — 50 МБ); nginx `client_max_body_size 55m`.
- Телефон: цифры `^375(25|29|33|44|17)\d{7}$`, хранится `+375XXXXXXXXX`.
- Способ связи: `call` / `viber` / `telegram` (подписи «Звонок», «Viber», «Telegram»).
- Хранение заявок — `LEADS__RETENTION_DAYS`, по умолчанию 365.
- Версия текста согласия — `2026-11-04`.
- Тексты для людей — по-русски, на «вы».

## Review Focus

- Двойное нажатие «Беру» двумя людьми одновременно — заявка у одного, второй видит, кто взял (условный `UPDATE`).
- Повторная правка сообщения тем же текстом → Telegram отвечает «message is not modified» — не ошибка.
- Нажатие кнопки у удалённой заявки (12 месяцев прошли) — ответ «Заявка уже удалена», без падения.
- Кириллица и HTML в имени/комментарии — экранируется (`parse_mode=HTML`).
- Кириллическое имя файла при скачивании из админки — корректный `Content-Disposition`.

---

### Task 1: модель, закрытое хранилище, админка

**Files:** create `backend/src/apps/leads/{__init__,apps,models,signals,admin}.py`, миграция `0001_initial`; modify `settings/settings.py` (INSTALLED_APPS, `PRIVATE_MEDIA_ROOT`, `STORAGES['private']`, `FILE_UPLOAD_TEMP_DIR`, Unfold sidebar), `backend/Dockerfile` (`/src/private`), `root/docker-compose.yaml` (том `private_media`), `root/docker-compose.dev.yaml` (`!override` томов), `.gitignore`; test `backend/src/tests/test_leads_admin.py`.

**Produces:** `Lead` (поля из spec + `tg_chat_id`, `tg_message_id`, `tg_file_sent`, `assignee_tg_id`, `assignee_name`, `assigned_at`), `Lead.ContactMethod`, `private_storage()`; post_delete удаляет файл; админка: файл скачивается по `admin:leads_lead_file`.

- [ ] Тесты: `test_file_download_requires_staff` (аноним → 302, `admin_client` → 200, attachment), `test_changelist_opens`, `test_delete_removes_file`.
- [ ] Модель, хранилище, админка, миграция; `pytest` зелёный.

### Task 2: `POST /api/leads/`

**Files:** create `apps/leads/{validators,serializers,views,urls}.py`; modify `settings/urls.py`, `settings.py` (throttle rates `leads_burst: 3/min`, `leads_day: 20/day`, `LEADS__MAX_FILE_BYTES`), `root/nginx/nginx.conf`; test `tests/test_leads_api.py`.

**Consumes:** `Lead`. **Produces:** `normalize_phone(str) -> str`, `validate_lead_file(UploadedFile)`; view ставит `notify_lead.delay(id)` через `transaction.on_commit`.

- [ ] Тесты: сохранение и нормализация телефона, IP и версия согласия; уведомление ставится после commit; плохой телефон, нет согласия → 400; honeypot → 201 без записи; PDF сохраняется под UUID в `PRIVATE_MEDIA_ROOT`; чужая сигнатура, `.exe`, большой файл → 400; четвёртая заявка за минуту → 429.
- [ ] Реализация; `pytest` зелёный.

### Task 3: отправка в Telegram

**Files:** create `apps/leads/telegram/{__init__,client,messages}.py`, `apps/leads/tasks.py`; modify `settings.py` (`TELEGRAM__BOT_TOKEN`, `TELEGRAM__CHAT_ID`, `PUBLIC_URL`), `pyproject.toml` (httpx), `.env.example`, compose env; test `tests/test_leads_telegram.py`.

**Produces:** `Bot.call(method, files=None, **params) -> Any`, `TelegramError(description, code, retry_after)` с `.retryable`, `get_bot() -> Bot | None`, `render_lead(lead) -> str`, `lead_keyboard(lead) -> dict`, задачи `notify_lead(lead_id)`, `sync_lead_message(lead_id)`.

- [ ] Тесты: HTML экранируется; `notify_lead` шлёт сообщение и документ ответом, сохраняет id; без токена — ничего; при сохранённом `tg_message_id` шлёт только файл; 400 от Telegram — без повторов.
- [ ] Реализация; `pytest` зелёный.

### Task 4: кнопки и `runbot`

**Files:** create `apps/leads/telegram/handlers.py`, `apps/leads/management/commands/runbot.py`; modify `admin.py` (правка ответственного → `sync_lead_message`), compose (`telegram_bot`); tests в `test_leads_telegram.py`.

**Produces:** `handle_update(bot, update: dict) -> None`.

- [ ] Тесты: «Беру» назначает и меняет кнопку; занятая — alert с именем; «Отказаться» — только взявший, после — ответ «снова свободна»; чужой чат игнорируется; удалённая заявка; `/start` в личке; `/chatid` в группе.
- [ ] Реализация; `pytest` зелёный.

### Task 5: удаление старых заявок

**Files:** modify `tasks.py` (`purge_old_leads() -> int`), `settings.py` (`CELERY_BEAT_SCHEDULE`, `LEADS__RETENTION_DAYS`); test `tests/test_leads_retention.py`.

- [ ] Тест: старая заявка и её файл удалены, свежая осталась.
- [ ] Реализация; `pytest` зелёный.

### Task 6: форма на фронте

**Files:** modify `web/src/components/LeadForm/LeadForm.tsx` (+ `.module.css`), `web/src/app/privacy/page.tsx`.

- [ ] `NEXT_PUBLIC_API_URL` задан → `fetch` multipart (`method` кодом, `page`, `consent_version`); 400 → ошибки полей, 429/сеть → общая ошибка с телефоном; не задан → имитация. Лимит 50 МБ, подсказка. Текст согласия и политика (Telegram, 12 месяцев).
- [ ] `npm run lint && npm run build`.

### Task 7: документы и проверки

- [ ] `decisions.md` (новые строки), `brief.md` («Заявка»), `backend/README.md`, `stack.md` (раздел 7), `web/README.md` («Что пока заглушка»).
- [ ] `uv run ruff check && uv run ruff format --check && uv run pytest`, `npm run lint && npm run build`, `docker compose config`.
