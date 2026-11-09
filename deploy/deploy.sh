#!/usr/bin/env bash
# Serverga yangi versiyani chiqaradi. Serverda ishga tushiriladi:
#
#   cd ~/print-hisob && git fetch && bash deploy/deploy.sh          # origin/main
#   bash deploy/deploy.sh <commit>                                  # aniq versiya
#   bash deploy/deploy.sh --allow-older <commit>                    # eski versiyaga qaytish
#   bash deploy/deploy.sh --force                                   # versiya o'zgarmasa ham
#
# Tartib: zaxira, kod, kutubxonalar, migratsiya, dashboard, restart, tekshiruv.
# Biror qadam o'tmasa kod va dashboard avvalgi holatiga qaytadi.
#
# Migratsiya orqaga qaytarilmaydi, zaxiradan tiklash esa qo'lda qilinadi. Shuning
# uchun migratsiyalar qo'shuvchi bo'lsin: eski kod yangi sxemada ishlay olishi kerak.
#
# `sudo` paroli so'raladi. Terminalsiz ishga tushirilsa, parol stdin'ning birinchi
# qatoridan o'qiladi.
#
# Butun skript `main` ichida: u o'zini ham yangilaydi, bash esa faylni bo'laklab
# o'qigani uchun ishlash davomida fayl almashsa adashib ketardi.

set -uo pipefail
umask 077

APP_DIR="${APP_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
BACKUP_ROOT="${BACKUP_ROOT:-$HOME/print-hisob-backups}"
SERVICE="${SERVICE:-printer-hisob-api}"
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:8000/health}"

# Serverda `npm install` lock faylga Linux paketlarini qo'shadi, shu o'zgarishga ruxsat bor.
LOCK_FILE="dashboard/package-lock.json"

SUDO_MODE=""
SUDO_PASSWORD=""
PREV=""
TARGET=""
FORCE=0
ALLOW_OLDER=0
DIST_BACKUP=""

say() { echo "==> $*"; }
die() { echo "XATO: $*" >&2; exit 1; }
log_result() { echo "$(date -Is) ${PREV:0:7} -> ${TARGET:0:7} $1" >>"$BACKUP_ROOT/deploy.log"; }

changed() { # changed <dan> <gacha> <yo'l>...
  local from=$1 to=$2
  shift 2
  ! git diff --quiet "$from" "$to" -- "$@"
}

run_sudo() {
  case "$SUDO_MODE" in
    nopass) sudo -n "$@" ;;
    tty) sudo "$@" ;;
    *) printf '%s\n' "$SUDO_PASSWORD" | sudo -S -p '' "$@" ;;
  esac
}

prepare_sudo() {
  if sudo -n true 2>/dev/null; then
    SUDO_MODE=nopass
  elif [ -t 0 ]; then
    SUDO_MODE=tty
    sudo -v || die "sudo ruxsati olinmadi"
  else
    SUDO_MODE=stdin
    IFS= read -r SUDO_PASSWORD || die "sudo paroli stdin orqali berilmadi"
    run_sudo -v 2>/dev/null || die "sudo paroli noto'g'ri"
  fi
}

switch_code() { # switch_code <dan> <gacha>
  if changed "$1" "$2" dashboard/package.json "$LOCK_FILE"; then
    git checkout -- "$LOCK_FILE" || return 1
  fi
  git reset --quiet --keep "$2"
}

install_backend() {
  (
    cd api || exit 1
    # Virtual muhit `uv` bilan qurilgan bo'lsa unda pip bo'lmaydi.
    if [ -x .venv/bin/pip ]; then
      .venv/bin/pip install --quiet --disable-pip-version-check -r requirements.txt </dev/null
    else
      uv pip install --quiet --python .venv/bin/python -r requirements.txt </dev/null
    fi
  )
}

install_dashboard() {
  (cd dashboard && npm install --no-audit --no-fund </dev/null)
}

restart_and_check() {
  run_sudo systemctl restart "$SERVICE" || return 1
  local _
  for _ in $(seq 1 30); do
    if curl -fsS -m 2 "$HEALTH_URL" 2>/dev/null | grep -q '"status":"ok"'; then
      sleep 3
      systemctl is-active --quiet "$SERVICE"
      return
    fi
    sleep 1
  done
  return 1
}

apply_new_version() {
  if [ "$FORCE" = 1 ] || changed "$PREV" "$TARGET" api/requirements.txt; then
    say "Backend kutubxonalari"
    install_backend || return 1
  fi

  say "Baza migratsiyasi"
  (cd api && .venv/bin/alembic upgrade head </dev/null) || return 1

  if [ "$FORCE" = 1 ] || changed "$PREV" "$TARGET" dashboard/package.json "$LOCK_FILE"; then
    say "Dashboard kutubxonalari"
    install_dashboard || return 1
  fi

  say "Dashboard yig'ilmoqda"
  (cd dashboard && npm run build </dev/null) || return 1

  say "Xizmat qayta ishga tushirilmoqda"
  restart_and_check
}

rollback() {
  say "Xato. Avvalgi versiyaga qaytarilmoqda: ${PREV:0:7}"
  switch_code "$TARGET" "$PREV" || {
    log_result "ROLLBACK_XATO"
    die "kodni qaytarib bo'lmadi, serverni qo'lda tekshiring"
  }
  if changed "$PREV" "$TARGET" api/requirements.txt; then install_backend; fi
  if changed "$PREV" "$TARGET" dashboard/package.json "$LOCK_FILE"; then install_dashboard; fi
  if [ -s "$DIST_BACKUP" ]; then
    rm -rf dashboard/dist && tar -xzf "$DIST_BACKUP" -C dashboard
  fi
  if restart_and_check; then
    log_result "QAYTARILDI"
    say "Avvalgi versiya ishlayapti: ${PREV:0:7}"
  else
    log_result "QAYTARILDI_XIZMAT_ISHLAMAYAPTI"
    say "Kod qaytarildi, lekin xizmat ishga tushmadi: journalctl -u $SERVICE -e"
  fi
  exit 1
}

main() {
  local ref="origin/main"
  while [ $# -gt 0 ]; do
    case "$1" in
      --force) FORCE=1 ;;
      --allow-older) ALLOW_OLDER=1 ;;
      -*) die "noma'lum parametr: $1" ;;
      *) ref="$1" ;;
    esac
    shift
  done

  cd "$APP_DIR" || die "$APP_DIR topilmadi"
  mkdir -p "$BACKUP_ROOT"
  exec 9>"$BACKUP_ROOT/deploy.lock"
  flock -n 9 || die "boshqa deploy ishlayapti"

  local dirty
  dirty=$(git status --porcelain | grep -v " $LOCK_FILE\$" || true)
  [ -z "$dirty" ] || die "serverda commit qilinmagan o'zgarishlar bor:
$dirty"

  git fetch --quiet origin || die "git fetch o'tmadi"
  PREV=$(git rev-parse HEAD)
  TARGET=$(git rev-parse --verify "$ref^{commit}") || die "versiya topilmadi: $ref"

  if [ "$PREV" = "$TARGET" ] && [ "$FORCE" != 1 ]; then
    say "Yangi versiya yo'q (${PREV:0:7})"
    exit 0
  fi
  if ! git merge-base --is-ancestor "$PREV" "$TARGET" && [ "$ALLOW_OLDER" != 1 ]; then
    die "${TARGET:0:7} joriy versiyaning davomi emas. Eski versiyaga qaytish uchun --allow-older bering"
  fi

  prepare_sudo

  say "Zaxira olinmoqda"
  local dump
  dump=$(bash deploy/backup.sh deploy | tail -n 1) && [ -s "$dump" ] || die "zaxira olinmadi, hech narsa o'zgarmadi"
  say "Zaxira: $dump"

  DIST_BACKUP="$BACKUP_ROOT/dist-before-deploy.tgz"
  rm -f "$DIST_BACKUP"
  if [ -d dashboard/dist ]; then
    tar -czf "$DIST_BACKUP" -C dashboard dist || die "dashboard zaxirasi olinmadi"
  fi

  say "Kod: ${PREV:0:7} -> ${TARGET:0:7}"
  switch_code "$PREV" "$TARGET" || die "kodni almashtirib bo'lmadi, hech narsa o'zgarmadi"

  if apply_new_version; then
    log_result "OK"
    say "Tayyor: ${TARGET:0:7} ishlayapti"
    exit 0
  fi
  rollback
}

main "$@"; exit $?
