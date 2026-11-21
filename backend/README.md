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

В dev при включённом S3 файлы с ключами `local/…` читаются с диска, пока локальная копия существует. После переноса одноимённого объекта в S3 и удаления копии dev читает объект из бакета. Удаление ключа `local/…` из dev-хранилища затрагивает только диск.

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
  apps/content/   настройки сайта (django-solo), вопрос-ответ, проекты, блог, акции, шоурум: API только на чтение,
                  html.py (чистка текста статей), widgets.py (точка фокуса фото и подсказки о размере в админке),
                  сигнал фронту обновить страницы; команда loaddemo
                  (заливает и каталог)
  apps/catalog/   категории, бренды (логотип, «гарантия до»), сроки изготовления,
                  серии (Series, наценка markup_percent), варианты (Variant), группы цветов и цвета (ColorGroup, Color), витрина (Showcase),
                  фото и файлы серии (SeriesImage, SeriesFile), курсы валют (CurrencyRate).
                  Импорт прайса Guardo и Nova: команда import_price; КЗТО — import_kzto (importers/kzto.py, kzto_page.py); Velar — import_velar (importers/velar.py); фото и PDF заводов — import_photos, import_files; курсы: rates.py, tasks.py; поиск (слова, раскладка, синонимы) — search.py. Тег кэша фронта — catalog
  tests/          pytest
```

Новое приложение — `src/apps/<name>/` с `apps.py` (`name = 'apps.<name>'`), в `INSTALLED_APPS`, URL — внутри `api/` в `settings/urls.py`.

## Каталог: импорт прайса и курсы

Наценка — в карточке каждой серии (`Series.markup_percent`), отдельно от надбавки за цвет. Миграция `catalog.0015` переносит текущие проценты брендов в их серии без изменения рассчитанных цен. После задания разных процентов сериям автоматический откат к одному проценту бренда блокируется, чтобы не потерять настройки.

Детали серии возвращают `range_steps`: уникальные размеры и число секций, собранные одним SQL-агрегатом. Next кэширует их вместе с деталями серии по тегу `catalog`; при запросах страниц таблицы списки размеров повторно не вычисляются.

```bash
uv run python src/manage.py import_price <путь к xlsx> [--sheet <лист>] [--dry-run]
```

Первый импорт создаёт серии неопубликованными, а группы цветов — по цветам, которые есть не меньше чем у 5 % артикулов серии. Повторный импорт группы и описания не трогает, а новые цвета выводит списком. Повёрнутые Retta и Torre — отдельные варианты: вариант определяют бренд, артикул и подключение. API без префикса серии: `/api/series/`, `/api/series/<slug>/`, `/api/series/<slug>/variants/`, `/api/variants/<article>/?series=&connection=`.

КЗТО — с сайта завода kztoradiator.ru (решение № 151), сеть нужна, файл не нужен:

```bash
uv run python src/manage.py import_kzto [--publish] [--no-pages] [--no-media] [--dry-run] [--feed <адрес или путь>]
```

Варианты, размеры, мощность и базовые цены в RUB — из YML-фида `kztoradiator.ru/yml-feed.xml`. Каждой категории радиаторов соответствует отдельная серия: 28 серий, H/V и В/Г разделены. Конвекторы/решётка — прежние 11 серий. Описание, полная галерея и PDF/XLSX — со страницы конкретного исполнения; `TARGETS` и `importers/kzto_series.py` задают принадлежность. Новые категории выводятся предупреждением; зеркала, завалинки, окантовка и защитные крышки исключены.

В существующей базе с объединёнными сериями **сначала** выполните перенос, затем обычный импорт. Сделайте резервную копию таблиц каталога и связей проектов; выясните фактическую БД/storage (локально может использоваться общий S3). Команда переноса по умолчанию ничего не меняет; `--series kzto-quadrum-neo-50` ограничивает пилот, `--report <path>` сохраняет план. PK, артикулы, текущие базовые цены и наценки сохраняются. Неоднозначные артикулы и повторяющиеся названия групп цветов останавливают перенос до записи. Ручные материалы и неоднозначные проекты остаются у архивной серии; файлы не удаляются.

```bash
uv run python src/manage.py split_kzto_series --feed <сохранённый XML> --dry-run
uv run python src/manage.py split_kzto_series --feed <сохранённый XML> --apply
uv run python src/manage.py import_kzto_connections --apply
uv run python src/manage.py sync_kzto_media --apply --report <path.json>
uv run python src/manage.py curate_kzto_gallery --apply
uv run python src/manage.py ensure_ral_options --apply
```

Команды без `--apply` показывают отчёт. `curate_kzto_gallery` применяет сохранённый визуальный отбор повторов только КЗТО через `SeriesImage.is_visible`, файлы не удаляются. Новые фото из реестра импортируются с учётом отбора; обычная синхронизация сохраняет ручное восстановление видимости. По умолчанию `ensure_ral_options` добавляет «Любой RAL — по запросу» опубликованным радиаторам КЗТО. Флаг `--brand radimax` выбирает опубликованные радиаторы Радимакс. Базовая цена сохраняется. `--series <slug>` можно повторять. Реестры источников и проверенных доплат: `src/apps/catalog/data/kzto_media_sources.json`, `kzto_connections.json` (2026-11-18). Свежий подтверждённый набор правил передаётся через `--source`; текущая дата не затирает ручную корректировку суммы. Медиа можно предварительно скачать в кэш: `--cache-dir <dir>`, имя файла — SHA256 полного исходного URL. В реестре фото размечены по содержимому, а не по пропорции. Превью родительской карточки загружается отдельно; 3D/CAD и видео перечисляются в отчёте как дополнительные материалы.

Повторный обычный импорт обновляет базовые цены и варианты, не восстанавливает объединение и не меняет правила доплат. Синхронизация медиа дополняет по исходному URL/хешу, проверяет реальные PDF/XLSX, сохраняет ручные материалы и не удаляет объекты S3. Фото уже заполненной серии и документы сверх шести не пропускаются. После применённых изменений команды отправляют одну инвалидацию `catalog`.

Подключения — отдельная модель `ConnectionOption`, базовый `Variant` не копируется. API `execution=kzto-<id>` ограничивает рядность и секции, проецирует подключение/термоклапан/монтаж и считает цену. Для отдельной строки передавайте тот же `execution` и текущие диапазоны: `/api/variants/<article>/?series=…&execution=…`. Цена конфигурации в RUB: `round(base * colour_multiplier) + surcharge_rub + base_adjustment_rub`, затем курс/наценка/округление BYN. Цвет не умножает фикс. Число в `tubes` — ряды труб в глубину, не число труб системы отопления.

Белые поля, вшитые в фото завода (вертикальный кадр, дополненный белым до горизонтального), импорт срезает сам (`photos.py`, решение № 157).

Витринные фото заводов — первыми в галерею серий (решения № 164, 166): рендеры guardo.ru по высотам (по две на положение) и плитки kztoradiator.ru (Ellipse, Quadrum 30/50, Neo 50); у Guardo ещё цветные рендеры по RAL и схемы подключений — в конец галереи (страницы высот, около минуты); у Velar — превью и интерьерные рендеры velarwh.ru (`importers/velar_photos.py`, отобраны вручную). Повторный запуск не дублирует; какие серии и картинки — `GUARDO_PAGES` и `KZTO_TILES` в `importers/factory_photos.py`:

```bash
uv run python src/manage.py import_photos [--brand guardo|kzto|velar|all] [--dry-run]
uv run python src/manage.py import_files [--brand guardo|all] [--dry-run]   # каталоги и паспорта PDF Guardo
```

Velar — прайс завода (xlsx, профильные радиаторы; решение № 166). Новые серии неопубликованные; повторный импорт обновляет варианты и цены, пропавшие скрывает (только у серий этого прайса), у серии заполняет пустые поля, описание собирает из прайса (`importers/velar_text.py`):

```bash
uv run python src/manage.py import_velar <путь к xlsx> [--publish] [--dry-run]
```

В Docker файл прайса сначала копируется в контейнер: `docker cp <xlsx> $(docker compose … ps -q backend):/tmp/velar.xlsx`.

Курсы валют берёт Celery beat, задача `update-currency-rates` в 01:10, из `api.nbrb.by` (серверу нужен исходящий HTTPS к этому адресу, ключ не нужен). Вручную — действие в админке «Обновить курсы сейчас».

## Контент локально

Настройки сайта (с видео шоурума), вопрос-ответ, проекты, блог, акции и шоурум — в админке, раздел «Сайт»; категории, бренды и сроки — раздел «Каталог». Наполнить демо-записями с фронта (вместе с фото из `web/public/images`):

```bash
docker compose -f docker-compose.yaml -f docker-compose.dev.yaml run --rm backend loaddemo   # из root/
```

Демо-команда и два JSON-набора нужны для воспроизводимого локального запуска и тестов. Запускайте её на отдельной базе и с отдельным хранилищем. Повторный запуск обновляет записи и настройки сайта. Чтобы правки сразу появлялись на `localhost:3000`, задайте одинаковый секрет в `root/.env` (`BACKEND__FRONTEND__REVALIDATE_URL=http://host.docker.internal:3000/api/revalidate`, `BACKEND__FRONTEND__REVALIDATE_SECRET`) и в `web/.env.local` (`REVALIDATE_SECRET`), см. `web/.env.example`. Без этого фронт обновит страницы сам — в течение часа, а сбросить кэш сразу можно из `web/`: `npm run revalidate` (`-- 3010` — фронт на другом порту). Сигнал из админки уходит только на один адрес — фронт, запущенный на другом порту, его не получит.

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
- Код — ruff (одинарные кавычки, 79 символов), сообщения коммитов — как в [`../AGENTS.md`](../AGENTS.md).
- Вызовы и поля с несколькими аргументами — по одному на строку, с запятой в конце: ruff format сохраняет столбик, но сам его не делает, если вызов влезает в строку.
- HTTP-коды — `rest_framework.status` в ответах DRF; тексты для людей — константами (бот — `apps/leads/telegram/texts.py`).

### Единый каталог

`ProductFamily` группирует исполнения; `Series.factory_orientation` задаётся по источнику, не пропорциям. `Series.offer_mode` явно выбирает готовые строки (`direct`) или базу с проверенными правилами (`configured`). `offers.py` строит SQL-проекцию предложений, общую для каталога, фасетов, таблицы и выбранной строки; фильтры применяются к одному предложению до пагинации. Неизвестный `thermovalve` — NULL.

`audit_catalog_attributes --report /tmp/attributes.json` работает без записи; `--apply` назначает линейки по реестру, а с `--velar-source <xlsx>` адресно исправляет неподтверждённые старые значения Velar. Ручные `attrs.confirmed_fields` сохраняются. Перед применением нужна резервная копия фактической БД. Повторный импорт не стирает подтверждённую вручную линейку; противоречие известного положения источнику требует разбора.

### Перенос Guardo/Velar и материалы

Сначала обычный импорт прайса на чистой БД, затем явный проверенный перенос объединённых серий. Существующая база: резервная копия фактической БД, отчёт пилота и только затем применение. Локально этап выполнен; команды не являются разрешением для сервера.

```bash
uv run python src/manage.py split_catalog_editions --source <xlsx> --series guardo-retta-3p --report /tmp/editions.json
uv run python src/manage.py split_catalog_editions --source <xlsx> --series guardo-retta-3p --report /tmp/editions.json --apply
uv run python src/manage.py sync_catalog_media --report /tmp/media.json
uv run python src/manage.py sync_catalog_media --apply --cache-dir /tmp/catalog-media --report /tmp/media.json
```

`--series` можно повторять для одного исходного прайса. Реестр `factory_editions.json` различает код **и** подключение Guardo; Velar — по заводскому листу. Новые неизвестные сочетания/геометрия блокируют перенос. Отчёт содержит PK, группы цветов, связи и fingerprint; apply проверяет исходное состояние в транзакции. Повторный импорт после переноса обновляет детей, не возрождает объединённую серию. Свидетельства прайса кэшируются в приватной папке с правами 0700 временного каталога по хешу источника/реестра/версии адаптера.

Старые `/legacy/` адреса поддерживают Guardo, Velar и КЗТО; без однозначного артикула показывают выбор. `ProductFamily.presentation_photo` сохраняет исходную презентацию, галереи детей ограничены подтверждённым положением. `SeriesFile.is_visible` управляет публичной ссылкой без удаления storage-объекта. Фотографии/документы дополняются по каноническому URL/хешу; Яндекс.Диск разрешается через public resources API, подписанные временные download URL в реестре не хранятся. Исходные XLSX и файлы `materials/` не меняются.

После миграции 0021 у уже разделённой БД заполните устойчивые ссылки старых групп цветов. Команда сначала показывает отчёт, неоднозначности останавливают применение:

```bash
uv run python src/manage.py backfill_legacy_color_groups --report /tmp/color-origins.json
uv run python src/manage.py backfill_legacy_color_groups --report /tmp/color-origins.json --apply
```

`ColorGroup.legacy_origin` сохраняет старый ID независимо от последующего переименования и изменения процента. `source_aliases` фотографий и документов запоминает дополнительные URL тех же байтов: повторное появление источника не создаёт видимую копию скрытой записи. Эти служебные поля не добавляют рабочие поля менеджеру.

## Радимакс

Исходные данные — `src/apps/catalog/data/radimax_price.csv`. Колонка `source` указывает на апрельский прайс АртТепло или соответствующую страницу презентации Соул/Стилл. Для Стилл исходные дробные ширины хранятся в `attrs`, публичное поле ширины округлено до миллиметра.

```bash
uv run python src/manage.py import_radimax
uv run python src/manage.py import_radimax --apply
uv run python src/manage.py sync_catalog_media \
  --source src/apps/catalog/data/radimax_media_sources.json \
  --local-dir ../output/radimax-sources \
  --report /tmp/radimax-media.json --local-media --apply
```

Импорт создаёт по карточке на заводской типоразмер. Новые карточки создаются черновиками. При переходе со старых сгруппированных серий варианты переезжают с прежними ID и флагом «В продаже». Повтор обновляет данные по стабильному артикулу. Для частичной загрузки используйте повторяемый `--series <slug>` в обеих командах. В режиме DEBUG флаг `--local-media` сохраняет новые файлы на диск в `media/local/`, даже когда остальной каталог использует S3. Для серверной загрузки используют обычный импорт медиа без этого флага.

## Материалы полотенцесушителей Guardo

Отобранные заводские фото, схемы и PDF шести серий с SHA-256 перечислены в `src/apps/catalog/data/guardo_towel_media_sources.json`. Локальную загрузку выполняет `sync_catalog_media`.

```bash
uv run python src/manage.py sync_catalog_media \
  --source src/apps/catalog/data/guardo_towel_media_sources.json \
  --report /tmp/guardo-towel-media.json --local-media --apply
```
