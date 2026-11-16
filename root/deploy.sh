#!/usr/bin/env bash
# Обновление контейнеров на сервере. Запускает .github/workflows/deploy.yml по SSH:
#   TAG=main GHCR_USER=<логин> ./deploy.sh <<< "<токен GHCR>"
# Токен приходит через stdin (не в аргументах — их видно в ps) и живёт до конца задачи CI.
set -euo pipefail

cd "$(dirname "$0")"

: "${TAG:?нужен TAG}"
: "${GHCR_USER:?нужен GHCR_USER}"
[[ -f .env ]] || { echo ".env не найден в $(pwd): создайте по .env.example" >&2; exit 1; }

read -r token
echo "$token" | docker login ghcr.io -u "$GHCR_USER" --password-stdin
trap 'docker logout ghcr.io >/dev/null' EXIT

export IMAGE_TAG="$TAG"
docker compose pull --quiet
# --wait: ждёт healthcheck; упавшие миграции или backend — красный деплой
docker compose up -d --remove-orphans --wait --wait-timeout 180

# Новый образ фронта собран без бэка, на демо-данных (web/src/data/api.ts). Сбрасываем
# все теги кэша: первый же заход соберёт страницы из админки. Теги — как в /api/revalidate
docker compose exec -T web node -e '
  fetch("http://127.0.0.1:3000/api/revalidate", {
    method: "POST",
    headers: { authorization: `Bearer ${process.env.REVALIDATE_SECRET}`, "content-type": "application/json" },
    body: JSON.stringify({ tags: ["site", "faq", "projects", "posts", "showroom", "catalog"] }),
  }).then((r) => { console.log("revalidate:", r.status); process.exit(r.ok ? 0 : 1); }, (e) => { console.error(e); process.exit(1); });
'
docker image prune -f

# Расписание — из репозитория: блок между метками переписывается при каждом деплое,
# остальные строки crontab пользователя deploy не трогаем
dir=$(pwd)
jobs="# art-teplo: begin (ставит deploy.sh, правьте в репозитории)
30 3 * * * $dir/backup.sh >> $dir/backup.log 2>&1
*/5 * * * * $dir/monitor.sh >> $dir/monitor.log 2>&1
# art-teplo: end"
{ { crontab -l 2>/dev/null || true; } | sed '/^# art-teplo: begin/,/^# art-teplo: end/d' | { grep -vF "$dir/backup.sh" || true; }; echo "$jobs"; } | crontab -
