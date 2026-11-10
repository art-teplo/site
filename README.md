# art-teplo.by

Новый сайт АртТепло — шоурума дизайн-радиаторов в Минске (ул. Леонида Беды, 39). Каталог для заявок без корзины: человек выбирает радиатор или проходит подбор и оставляет телефон, менеджер перезванивает.

| Папка | Что внутри |
| --- | --- |
| [`web/`](web/) | фронт на Next.js 16 — как запустить и правила кода в [`web/README.md`](web/README.md) |
| [`backend/`](backend/) | API и админка на Django + DRF + Unfold — [`backend/README.md`](backend/README.md) |
| [`root/`](root/) | docker compose, nginx и скрипт деплоя |
| [`.github/`](.github/) | CI, деплой и Dependabot |
| [`DESIGN.md`](DESIGN.md) | дизайн-система сайта: цвета, шрифт, компоненты, правила |
| [`docs/`](docs/) | бриф ([`brief.md`](docs/brief.md)), журнал решений ([`decisions.md`](docs/decisions.md)), фото, стек |
| [`materials/`](materials/) | исходники: документы заказчика и визуальные референсы, только для чтения |

Сейчас это демо для заказчика (сервер ActiveCloud, фронт и бэк в Docker за nginx; закрыто от поисковиков, часть фото взята из открытых источников). Бэкенд на Django + DRF — пока каркас без моделей, см. [`docs/stack.md`](docs/stack.md).

Ветки и сообщения коммитов — gitflow и Conventional Commits, подробнее в [`CLAUDE.md`](CLAUDE.md).
