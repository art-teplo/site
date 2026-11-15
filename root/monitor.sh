#!/usr/bin/env bash
# Алерты о сервере в Telegram: диск, ночной бэкап, сайт и API, контейнеры.
# Пишет только при смене состояния («сломалось» / «починилось»), раз в сутки при
# незакрытой беде напоминает. Нагрузка — df, curl и docker ps раз в 5 минут.
# На сервере — cron пользователя deploy раз в 5 минут, ставит deploy.sh.
# Свой бот, не бот заявок: в .env MONITOR__TELEGRAM_BOT_TOKEN (из @BotFather)
# и MONITOR__TELEGRAM_CHAT_ID — ваш личный чат с этим ботом. Узнать id: написать
# боту /start, затем ./monitor.sh chatid. Без обоих значений алерты только в лог.
# Проверить доставку: ./monitor.sh test
set -uo pipefail

cd "$(dirname "$0")"
[[ -f .env ]] || { echo ".env не найден в $(pwd)" >&2; exit 1; }

env_get() { grep -E "^$1=" .env | tail -1 | cut -d= -f2- | sed -E "s/^['\"]//; s/['\"]$//"; }

DISK_LIMIT=80        # % занятого места на /
BACKUP_MAX_AGE=26    # часов с последнего удачного бэкапа (cron — в 3:30)
SITE_FAILS=2         # столько проверок подряд без ответа — алерт (деплой перезапускает контейнеры)
REMIND_EVERY=86400   # секунд между напоминаниями о незакрытой беде

token=$(env_get MONITOR__TELEGRAM_BOT_TOKEN)
chat=$(env_get MONITOR__TELEGRAM_CHAT_ID)
port=$(env_get NGINX_PORT)
base="http://127.0.0.1:${port:-80}"
state=.monitor

# Токен — через конфиг curl на stdin, не аргументом: аргументы видно в ps
tg() { printf 'url = "https://api.telegram.org/bot%s/%s"\n' "$token" "$1" | curl -sSf -K - -m 15 "${@:2}"; }

send() {
  [[ -n "$token" && -n "$chat" ]] || { echo "$(date -Is) нет токена или chat id: $1"; return; }
  tg sendMessage -o /dev/null --data-urlencode "chat_id=$chat" --data-urlencode "text=🖥 art-teplo: $1" ||
    echo "$(date -Is) не отправилось: $1"
}

case "${1:-}" in
  test) send "проверка алертов, всё работает"; exit ;;
  # Кто писал боту: id и имя — id вписать в MONITOR__TELEGRAM_CHAT_ID
  chatid)
    [[ -n "$token" ]] || { echo "MONITOR__TELEGRAM_BOT_TOKEN не задан" >&2; exit 1; }
    tg getUpdates | grep -oE '"chat":\{"id":-?[0-9]+,"(first_name|title)":"[^"]*"' |
      sed -E 's/.*"id":(-?[0-9]+),"[a-z_]+":"(.*)"/\1 \2/' | sort -u
    exit ;;
esac

mkdir -p "$state"
declare -A LABEL=([disk]="место на диске" [backup]="ночной бэкап" [site]="сайт" [api]="API" [containers]="контейнеры")

# check <имя> <ok|fail> <текст беды> [<сколько fail подряд нужно>]
check() {
  local name=$1 status=$2 text=$3 need=${4:-1}
  local file="$state/$name" fails=0 alerted=0 at=0 now
  now=$(date +%s)
  [[ -f "$file" ]] && read -r fails alerted at < "$file"
  if [[ "$status" == ok ]]; then
    ((alerted)) && send "✅ снова в порядке: ${LABEL[$name]}"
    rm -f "$file"
    return
  fi
  fails=$((fails + 1))
  if ((fails >= need)) && { ((!alerted)) || ((now - at >= REMIND_EVERY)); }; then
    send "🔴 $text"
    alerted=1 at=$now
  fi
  echo "$fails $alerted $at" > "$file"
}

# Диск
used=$(df --output=pcent / | tail -1 | tr -dc 0-9)
check disk "$([[ $used -lt $DISK_LIMIT ]] && echo ok || echo fail)" \
  "диск занят на ${used}% (порог ${DISK_LIMIT}%): df -h, docker system df"

# Бэкап: последняя строка «ok s3://…» в backup.log моложе BACKUP_MAX_AGE часов
last=$(grep -E '^[0-9T:+-]+ ok s3://' backup.log 2>/dev/null | tail -1 | cut -d' ' -f1)
age=999999
[[ -n "$last" ]] && age=$(( ($(date +%s) - $(date -d "$last" +%s)) / 3600 ))
check backup "$([[ $age -lt $BACKUP_MAX_AGE ]] && echo ok || echo fail)" \
  "ночной бэкап базы не прошёл (последний удачный: ${last:-нет}); смотрите backup.log"

# Сайт и API — через nginx на хосте
http() { curl -s -o /dev/null -m 10 -w '%{http_code}' "$base$1"; }
code=$(http /)
check site "$([[ $code == 200 ]] && echo ok || echo fail)" "сайт не отвечает (/ → ${code})" "$SITE_FAILS"
code=$(http /api/health/)
check api "$([[ $code == 200 ]] && echo ok || echo fail)" \
  "API не отвечает (/api/health/ → ${code}): база, Redis или Django" "$SITE_FAILS"

# Контейнеры: упавшие или нездоровые
bad=$(
  docker ps -a --filter label=com.docker.compose.project=art-teplo --format '{{.Names}} {{.Status}}' | grep -Ev ' Up |Exited \(0\)'  # migrate завершается с кодом 0
  docker ps --filter health=unhealthy --format '{{.Names}} unhealthy'
)
check containers "$([[ -z "$bad" ]] && echo ok || echo fail)" "контейнеры не работают: ${bad//$'\n'/; }" "$SITE_FAILS"
