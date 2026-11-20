# Единые данные, фильтры и управление каталогом

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking. Делегирование реализации только по отдельному выбору пользователя; коммитов без просьбы нет.

**Статус:** утверждён 18.11.2026, этап A реализован локально и проверен;425backend-тестов,12node-тестов, lint/build, три ширины. Fresh review выполнено, существенные замечания исправлены. Без коммитов/push/деплоя.

**Goal:** Общий каталог и страницы серий получают одинаковые итоговые варианты; админка и интерфейс используют одни понятные признаки для четырёх брендов.

**Architecture:** Существующая Series остаётся техническим исполнением и получает ссылку на ProductFamily. Сервис предложений объединяет прямые прайсовые строки и вычисленные конфигурации КЗТО без постоянного копирования вариантов; существующие API-адреса сохраняются. Перенос Guardo/Velar и медиа вынесен в [план B](2026-11-18-unified-catalog-rollout.md).

**Tech Stack:** Django/DRF, PostgreSQL, текущие импортёры, Next.js/React, CSS Modules.

**Spec:** [Единая схема каталога](../specs/2026-11-18-unified-catalog-design.md).

## Global Constraints

- Сохранять исходные PK, артикулы, цены, группы цветов, наценки и старые ссылки.
- Не выводить положение из пропорций/GOR и не создавать H/V Nova/Pilon.
- Неизвестное значение не превращать в «нет», «настенный» или придуманную цену.
- Фикс КЗТО добавляется после процента цвета; текущая политика цены по запросу сохраняется.
- Общий S3: без удаления или замены существующих объектов.
- Только локальная реализация после утверждения; без коммитов, push и деплоя.

## Review Focus

- Фильтры всех признаков должны совпасть на одном предложении; регрессия перекрёстного совпадения — задача 3.
- Неподтверждённое отсутствие клапана не должно попасть в фильтр «без клапана» — задачи 1/3.
- Цвет/границы цены/фикс/курс должны совпасть в карточке, таблице и выбранной строке — задачи 2/3.
- Старые ссылки и смена подключения не должны терять положение/сторону подачи — задачи 3/5.
- Число SQL-запросов и объём сериализации не должны расти на каждую строку/правило — задачи 2/3.

## Ответственность файлов

`models.py` — связь линейки/исполнения и неизвестный клапан; `offers.py` — единое множество предложений/поиск/агрегации; `offer_pricing.py` — выражения цены PostgreSQL с проверкой против текущей Python-формулы; `configurations.py` — адаптер прежних ключей КЗТО. `views.py`, `filters.py`, `schema.py`, `serializers.py` используют сервис, не создают свою альтернативную цену. `admin.py`/новый `admin_forms.py` дают рабочие формы, не смешивают исходный Variant с итоговым предложением. Frontend types/API/общие селекторы не зависят от названия бренда.

## Task 1: Линейка и достоверность признаков

**Files:** Modify `backend/src/apps/catalog/models.py`, `importers/xlsx.py`, `importers/velar.py`, `importers/kzto.py`; Create `data/product_families.json`, `importers/product_families.py`, `migrations/0019_unified_catalog.py`, `management/commands/audit_catalog_attributes.py`; Test `src/tests/test_catalog_families.py`, текущие `test_catalog_import.py`/`test_catalog_velar.py`/`test_catalog_kzto.py`.

**Interfaces:** `ProductFamily(brand, category, key, name)` с уникальным `(brand,key)`; `Series.family` nullable FK(PROTECT), `factory_orientation` h/v/пусто, `offer_mode` direct/configured с default direct; `Variant.thermovalve: bool | None`. `family_for_target(brand_slug: str, series_slug: str) -> dict | None` читает явный реестр. Команда атрибутов по умолчанию отчёт; `--apply` меняет только перечисленные источником PK/значения и сохраняет отчёт до/после. Для существующих проверенных КЗТО режим configured включается отдельным применением после полного покрытия базовых вариантов, не автоматически при миграции старой серверной базы.

- [x] Закрепить тестами: семейство чужого бренда/категории запрещено; V270×680 остаётся V; Nova/Pilon не получают H/V; неизвестный клапан сериализуется null; пустое положение наследует известную Series, противоречие запрещено; добавление правила не переключает direct, неполное покрытие блокирует configured.
- [x] Выполнить новые тесты и убедиться в ожидаемом FAIL до реализации.
- [x] Добавить модели/миграцию и явный реестр существующих серий без переноса вариантов; нормализацию неизвестных сделать отдельной адресной командой. Не очищать явные False/монтаж других брендов без свидетельства.
- [x] Обновить импортёры: использовать подтверждённые признаки/реестр, поддерживать неизвестное; повторный импорт не стирает ручные подтверждённые значения без отчёта конфликта.
- [x] Из `backend/`: `uv run pytest src/tests/test_catalog_families.py src/tests/test_catalog_import.py src/tests/test_catalog_velar.py src/tests/test_catalog_kzto.py`; ожидается PASS. `makemigrations --check --dry-run` не предлагает дополнительных миграций.

## Task 2: Единое предложение и цена

**Files:** Create `backend/src/apps/catalog/offers.py`, `offer_pricing.py`; Modify `configurations.py`, `pricing.py`; Test `src/tests/test_catalog_offers.py`.

**Interfaces:** `OfferQuery` — read-only объект SQL-запроса. `offer_query(variants: QuerySet[Variant], *, color: str | None, rate: Decimal | None) -> OfferQuery`; `.filter(parsed: dict) -> OfferQuery`, `.page(number: int, size: int) -> list[Offer]`, `.count() -> int`, `.series_ids()`, `.price_bounds()`. `Offer` содержит variant_id, series_id, article, configuration_key, configuration_label, tubes, orientation/mount/thermovalve с неизвестными null, connection, сторону подачи, размеры, power_w, price. Прямая строка имеет configuration_key=null; КЗТО сохраняет `kzto-<PK>`. Стабильность стороны 5–7/9–7 обеспечивается явным реестром правил, а не объединением по bottom_center.

- [x] Создать тесты на прямой прайс, КЗТО 6007/4478, напольный фикс2785, процент цвета до обоих фиксов, отсутствие курса/цены, RAL по запросу и точное множество секций.
- [x] Увидеть FAIL новых тестов.
- [x] Построить SQL-отношение прямых строк для offer_mode=direct и допустимых пар Variant/ConnectionOption для configured: совпадают серия, рядность и секции. Базовое нулевое правило включается один раз, исходная строка не дублируется. Не подменять геометрию неподтверждённым вариантом монтажа. Не сериализовать всё множество до фильтрации/пагинации.
- [x] Реализовать выражения цены с теми же Decimal/ROUND_HALF_UP и выбором групп, что текущая Python-формула. Сравнить SQL и `configured_price` на матрице граничных округлений, доступности групп и обоих типов цены.
- [x] `uv run pytest src/tests/test_catalog_offers.py src/tests/test_kzto_configurations.py src/tests/test_catalog.py` — PASS.

## Task 3: Каталог, фасеты, таблица и выбранная строка

**Files:** Modify `views.py`, `filters.py`, `schema.py`, `serializers.py`, `configurations.py`; Test `test_catalog_api.py`, `test_catalog_offers.py`, `test_kzto_configurations.py`.

**Interfaces:** прежние `/api/series/`, `/api/series/<slug>/`, `/variants/`, `/api/variants/<article>/` используют OfferQuery. Фильтры `orientation`, `tubes`, `mount`, `thermovalve` и `connection` независимы. Legacy `execution` и новые независимые параметры нормализуются одним адаптером. Публичный ответ сохраняет существующие ключи; добавляет итоговые признаки, ключ конфигурации и подпись счётчика «конфигурации». Материалы/диапазоны серии ограничены конкретным исполнением.

- [x] Закрепить FAIL: центральное подключение находит Гармонию в общем каталоге. При одинаковом execution=kzto-14 и остальных ограничениях обе поверхности учитывают один набор из40 предложений на уровне сервиса; каталог возвращает карточку Гармонии, а не40карточек. Без execution центральный фильтр учитывает объединение всех допустимых рядностей/сторон, а не обязан равняться40. Совместные несовместимые признаки не дают ложного совпадения; неизвестный клапан не равен False.
- [x] Добавить проверки одинаковых цен/фасетов при цвете и диапазонах, конфигурации выбранного артикула, legacy URL H и центральных сторон подачи. Проверить артикул с ценой по запросу и нецветовые фильтры. Конфликт execution с thermovalve/mount/connection даёт пустую таблицу и404 выбранной строки, без смены конфигурации сервером.
- [x] Подключить единый сервис во все четыре пути, цены карточек и фасеты; убрать альтернативные фильтры по исходному подключению там, где нужны итоговые признаки. Сохранять семантику self-excluding facets.
- [x] Пагинировать в БД; закрепить отсутствие N+1 на фикстурах10/100 предложений и отсутствие обращения к image.storage ради каталожного фильтра. Счётчик карточек не смешивать со счётчиком предложений.
- [x] `uv run pytest src/tests/test_catalog_api.py src/tests/test_catalog_offers.py src/tests/test_kzto_configurations.py` — PASS; проверить одинаковую проекцию для прямых и вычисленных строк.

## Task 4: Рабочая админка

**Files:** Modify `admin.py`, `models.py`, `settings/settings.py`, `core/groups.py`; Create `admin_forms.py`; Test `test_admin_access.py`, `test_catalog_models.py`.

**Interfaces:** `ConnectionOptionForm` предоставляет `configuration_surcharge_rub` как сумму двух фиксов и `allowed_sections` как набор существующих секций выбранной рядности. Суммарное значение сохраняется в surcharge_rub после вычета неизменной установочной части; source_id/source_url/checked_on/evidence и исходная разбивка readonly в collapse. Ссылка из Series ведёт к её правилам; предпросмотр использует сервис предложений задачи2.

- [x] Проверить сохранение общей суммы без изменения итоговой цены, отказ суммы меньше установочной части, нецелые/повторные/чужие секции, менеджерские права и ссылки на правила своей серии.
- [x] Выполнить тесты, подтвердить FAIL, затем реализовать формы/валидацию/подписи и связанные подключения в Series.
- [x] Сделать подписи «Базовые варианты», «Доступные подключения», «Доплата за конфигурацию, RUB», «Доступные секции», «Источник данных»; сохранить рабочую ссылку в боковом меню. Создание новых непроверенных правил вручную отключить, редактирование существующих и проверяемый импорт сохранить.
- [x] `uv run pytest src/tests/test_admin_access.py src/tests/test_catalog_models.py` — PASS. Проверить базовую/настроенную цену в форме без сохранения нового Variant.

## Task 5: Общие параметры и контролы фронта

**Files:** Modify `web/src/data/types.ts`, `catalog-map.ts`, `api.ts`, `lib/catalog-query.ts`, `series-query.ts`, `series-selection.ts`, `components/PipeChips/*`, `sections/series/SeriesBody.tsx`, `SeriesVariants.tsx`/CSS, `SeriesHero.tsx`; Create `components/ParameterChoices/ParameterChoices.tsx` и CSS; Modify `DESIGN.md`.

**Interfaces:** ParameterChoices принимает label, value, items, onSelect без проверки бренда. PipeChips отвечает только за схемы/уточнение подключения; рядность/монтаж/положение выводятся из данных. Неизвестные значения отображаются честно; единственное значение — подпись. Формы:12px текстовые/числовые,20px схемы,8px кнопки, круглые цвета.

- [x] Дополнить существующие node-тесты значимыми проверками query/выбора: смена подключения сохраняет положение, сторону и совместимый артикул; атомарно удаляет только устаревшие параметры прежнего подключения; неизвестный клапан не становится false; legacy execution остаётся доступен. Увидеть FAIL.
- [x] Обновить типы/маппинг и единый разбор query на сервере/клиенте; реализовать общие контролы и удалить брендовые различия «Исполнение/Вариант подключения». Остальные категории каталога сохраняют свой смысл полей.
- [x] Обновить DESIGN.md и заменить pill-форму именно селекторов; состояния красной рамки/focus/disabled/hover/active едины. Не менять цвета, шрифт и общий стиль сайта.
- [x] Проверить375/768/1440, клавиатуру, уменьшение движения, длинные названия, пустую таблицу, смену цвета и заявку. Node-тесты, `npm run lint && npm run build` — PASS.

## Task 6: Приёмка этапа A

**Files:** docs/brief.md, docs/admin-guide.md, docs/decisions.md, docs/todo.md, backend/README.md, web/README.md; новый отчёт `docs/research/unified-catalog-core-result.json`.

- [x] Выполнить `uv run ruff check && uv run ruff format --check && uv run pytest`, `uv run python src/manage.py makemigrations --check --dry-run` из backend; node-тесты/lint/build из web.
- [x] Сохранить сверку базовых PK/цен/цветов до/после, одинаковых доступных предложений и цен между четырьмя API/экранами. Ни разделение Guardo/Velar, ни массовая загрузка в этот этап не входят.
- [x] Обновить руководство и решения только по фактически реализованному поведению; отметить этап A отдельно от B. `git diff --check` — чисто.
