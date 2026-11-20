# Инфраструктура и CI

Общие правила — в `../AGENTS.md`. Перед правками прочитай `../docs/stack.md` (особенно раздел 7), соответствующие решения в `../docs/decisions.md` и сами файлы в `root/` и `../.github/`.

- На сервер файлы `root/` доставляет `.github/workflows/deploy.yml`, применяет `deploy.sh`. Расписание бэкапа и мониторинга также задаёт `deploy.sh`. На сервере вручную меняется только `/opt/art-teplo/.env`.
- Секреты в `.env` не печатай. Для проверки Compose используй отдельную временную копию `root/` с `.env.example`, скопированным в `.env`; существующий локальный `.env` не перезаписывай. Полный вывод `docker compose config` с рабочим окружением может раскрыть секреты — используй `config -q`.
- Продакшен и dev-overlay различаются: опубликованные порты БД/Redis и bind mounts из `docker-compose.dev.yaml` не переносятся в прод.
- nginx заменяет клиентский `X-Forwarded-For` своим `$remote_addr`; это связано с `NUM_PROXIES` DRF и учётом IP. Изменение цепочки прокси проверяй с настройками бэка.
- Сборки и публикация образов в GHCR связаны с фильтрами путей в CI. Публикация из `main` и ручной деплой — отдельные действия; локальная проверка не разрешает запуск релиза.
- Запуск деплоя, восстановление дампа и изменения на сервере требуют соответствующей просьбы пользователя. Исторический статус сервера в документах не подтверждает текущее состояние.

Проверки без запуска контейнеров, из временной копии `root/` с примером окружения:

```bash
docker compose config -q
docker compose -f docker-compose.yaml -f docker-compose.dev.yaml config -q
docker compose -f docker-compose.yaml -f docker-compose.dev.yaml --profile web config -q
bash -n deploy.sh
bash -n backup.sh
bash -n monitor.sh
```

При изменениях workflow сверь условия запуска, фильтры путей и разрешения с `../.github/workflows/ci.yml` и `deploy.yml`. Фактический результат GitHub Actions подтверждается отдельно.
