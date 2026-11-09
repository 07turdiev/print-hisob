#!/usr/bin/env bash
# Bazaning to'liq zaxirasini oladi, o'qilishini tekshiradi va eskilarini o'chiradi.
#
#   bash deploy/backup.sh daily     # har kecha, cron orqali
#   bash deploy/backup.sh deploy    # deploy.sh har chiqarishdan oldin chaqiradi
#   bash deploy/backup.sh manual    # qo'lda
#
# Oxirgi qatorda zaxira fayli yo'li chiqadi.
set -euo pipefail
umask 077

LABEL="${1:-manual}"
APP_DIR="${APP_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
BACKUP_ROOT="${BACKUP_ROOT:-$HOME/print-hisob-backups}"
DIR="$BACKUP_ROOT/db"

case "$LABEL" in
  daily) KEEP=14 ;;
  deploy) KEEP=10 ;;
  *) KEEP=5 ;;
esac

cd "$APP_DIR/api"
eval "$(.venv/bin/python - <<'PY'
from pathlib import Path
from urllib.parse import unquote, urlsplit
import shlex

for line in Path(".env").read_text().splitlines():
    if line.startswith("DATABASE_URL="):
        url = urlsplit(line.split("=", 1)[1].strip().replace("+asyncpg", ""))
        values = (url.hostname, str(url.port or 5432), url.username, url.path.lstrip("/"), unquote(url.password or ""))
        print("export PGHOST=%s PGPORT=%s PGUSER=%s PGDATABASE=%s PGPASSWORD=%s" % tuple(map(shlex.quote, values)))
PY
)"

mkdir -p "$DIR"
FILE="$DIR/$LABEL-$(date +%Y%m%d-%H%M%S).dump"
TMP="$FILE.tmp"
trap 'rm -f "$TMP"' EXIT

pg_dump -Fc -f "$TMP" 2> >(grep -v 'No existing cluster' >&2 || true)
pg_restore -l "$TMP" 2>/dev/null | grep -q 'TABLE DATA public print_jobs' || {
  echo "XATO: zaxira fayli o'qilmadi yoki print_jobs yo'q" >&2
  exit 1
}
mv "$TMP" "$FILE"

ls -1t "$DIR/$LABEL"-*.dump | tail -n +"$((KEEP + 1))" | xargs -r rm -f --
echo "$FILE"
