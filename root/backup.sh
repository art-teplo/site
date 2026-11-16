#!/usr/bin/env bash
# Бэкап базы в S3 (бакет BACKUP__S3_BUCKET, ключи — BACKEND__S3__* из .env).
# Сколько копий хранить, решает правило бакета (удаление через 14 дней), не скрипт.
# На сервере — cron пользователя deploy в 3:30, ставит deploy.sh.
# Локально, с dev-compose:
#   COMPOSE="docker compose -f docker-compose.yaml -f docker-compose.dev.yaml" ./backup.sh
# Восстановление — docs/stack.md, «Бэкап базы».
set -euo pipefail

cd "$(dirname "$0")"
[[ -f .env ]] || { echo ".env не найден в $(pwd)" >&2; exit 1; }

read -ra compose <<< "${COMPOSE:-docker compose}"
AWS_CLI_IMAGE=amazon/aws-cli:2.40.2

env_get() { grep -E "^$1=" .env | tail -1 | cut -d= -f2- | sed -E "s/^['\"]//; s/['\"]$//"; }

bucket=$(env_get BACKUP__S3_BUCKET)
endpoint=$(env_get BACKEND__S3__ENDPOINT_URL)
AWS_ACCESS_KEY_ID=$(env_get BACKEND__S3__ACCESS_KEY_ID)
AWS_SECRET_ACCESS_KEY=$(env_get BACKEND__S3__SECRET_ACCESS_KEY)
: "${bucket:?BACKUP__S3_BUCKET не задан}" "${endpoint:?BACKEND__S3__ENDPOINT_URL не задан}"
: "${AWS_ACCESS_KEY_ID:?ключ S3 не задан}" "${AWS_SECRET_ACCESS_KEY:?ключ S3 не задан}"
# Ключи уходят в docker run через окружение, не аргументами: аргументы видно в ps
export AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY

dump=$(mktemp)
trap 'rm -f "$dump"' EXIT

# -Fc: свой сжатый формат pg_dump, восстанавливается pg_restore
"${compose[@]}" exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' < /dev/null > "$dump"
# Дамп читается целиком — иначе в бакет уйдёт обрывок
"${compose[@]}" exec -T postgres pg_restore --list < "$dump" > /dev/null

name="db/art-teplo-$(date +%F-%H%M).dump"
docker run --rm -i --quiet \
  -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY -e AWS_DEFAULT_REGION=us-east-1 \
  "$AWS_CLI_IMAGE" --endpoint-url "$endpoint" --only-show-errors \
  s3 cp - "s3://$bucket/$name" < "$dump"

echo "$(date -Is) ok s3://$bucket/$name $(du -h "$dump" | cut -f1)"
