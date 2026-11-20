# art-teplo.by

Новый сайт АртТепло — шоурума дизайн-радиаторов в Минске (ул. Леонида Беды, 39). Каталог для заявок без корзины: человек выбирает радиатор или проходит подбор и оставляет телефон, менеджер перезванивает.

| Папка | Что внутри |
| --- | --- |
| [`web/`](web/) | фронт на Next.js 16 — как запустить и правила кода в [`web/README.md`](web/README.md) |
| [`backend/`](backend/) | API и админка на Django + DRF + Unfold — [`backend/README.md`](backend/README.md) |
| [`root/`](root/) | docker compose, nginx и скрипт деплоя |
| [`.github/`](.github/) | CI, деплой и Dependabot |
| [`DESIGN.md`](DESIGN.md) | дизайн-система сайта: цвета, шрифт, компоненты, правила |
| [`docs/`](docs/) | бриф ([`brief.md`](docs/brief.md)), что осталось ([`todo.md`](docs/todo.md)), журнал решений ([`decisions.md`](docs/decisions.md)), стек и сервер ([`stack.md`](docs/stack.md)), фото; `superpowers/` — архив планов и спецификаций по этапам |
| [`materials/`](materials/) | исходники: документы заказчика и визуальные референсы, только для чтения |

Старый WordPress в `old-version/` и промежуточные выгрузки из `output/` хранятся локально. Исходные таблицы и реестры, которые читают команды импорта, находятся в `backend/src/apps/catalog/data/`. Для локальной разработки есть [демо-набор бэкенда](backend/README.md#контент-локально) и встроенные данные фронта для сборки без API.

Сейчас это демо для заказчика: сервер ActiveCloud, фронт и бэк в Docker за nginx, пока по IP и без HTTPS; закрыто от поисковиков, часть фото взята из открытых источников. Бэк держит заявки (уведомления в Telegram), контент сайта и каталог с импортом прайса. Что готово и что осталось — [`docs/todo.md`](docs/todo.md), как устроено — [`docs/stack.md`](docs/stack.md).

Ветки и сообщения коммитов — gitflow и Conventional Commits, подробнее в [`AGENTS.md`](AGENTS.md). Как работать с документацией и контекстом в Codex, Claude Code и ChatGPT — [`docs/ai-workflow.md`](docs/ai-workflow.md).
