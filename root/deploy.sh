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
docker image prune -f
