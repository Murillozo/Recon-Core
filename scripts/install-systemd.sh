#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="/opt/recon-core"
SERVICE_USER="recon"
TELEGRAM_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
ENABLE_SERVICES=1
START_SERVICES=1
COPY_PROJECT=1

usage() {
  cat <<'USAGE'
Usage: sudo ./scripts/install-systemd.sh [options]

Installs Recon Core as two systemd services:
  - recon-bot.service    (Telegram command bot)
  - recon-worker.service (SQLite queue worker)

Options:
  --install-dir PATH       Install/copy project to PATH (default: /opt/recon-core)
  --user USER              Linux service user (default: recon)
  --telegram-token TOKEN   Telegram bot token to write into PATH/.env
  --skip-copy              Do not copy the current checkout into --install-dir
  --no-enable              Do not enable services at boot
  --no-start               Do not start/restart services after installing
  -h, --help               Show this help

Environment:
  TELEGRAM_BOT_TOKEN       Used when --telegram-token is not provided

Examples:
  sudo TELEGRAM_BOT_TOKEN='123:ABC' ./scripts/install-systemd.sh
  sudo ./scripts/install-systemd.sh --install-dir /srv/recon-core --user recon --no-start
USAGE
}

log() { printf '[install-systemd] %s\n' "$*"; }
err() { printf '[install-systemd] ERROR: %s\n' "$*" >&2; }

need_arg() {
  local option="$1"
  local value="${2:-}"
  if [[ -z "$value" || "$value" == --* ]]; then
    err "$option requires a value"
    exit 2
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --install-dir)
      need_arg "$1" "${2:-}"
      INSTALL_DIR="$2"
      shift 2
      ;;
    --user)
      need_arg "$1" "${2:-}"
      SERVICE_USER="$2"
      shift 2
      ;;
    --telegram-token)
      need_arg "$1" "${2:-}"
      TELEGRAM_TOKEN="$2"
      shift 2
      ;;
    --skip-copy)
      COPY_PROJECT=0
      shift
      ;;
    --no-enable)
      ENABLE_SERVICES=0
      shift
      ;;
    --no-start)
      START_SERVICES=0
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      err "Unknown option: $1"
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$INSTALL_DIR" || -z "$SERVICE_USER" ]]; then
  err "--install-dir and --user cannot be empty"
  exit 2
fi

if [[ "${EUID}" -ne 0 ]]; then
  err "Run as root, for example: sudo TELEGRAM_BOT_TOKEN='...' $0"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
INSTALL_DIR="$(readlink -m "$INSTALL_DIR")"

for cmd in python3 systemctl; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    err "Required command not found: $cmd"
    exit 1
  fi
done

if [[ "$COPY_PROJECT" -eq 1 ]] && ! command -v rsync >/dev/null 2>&1; then
  err "rsync is required when copying the project. Install rsync or use --skip-copy."
  exit 1
fi

run_as_user() {
  if command -v runuser >/dev/null 2>&1; then
    runuser -u "$SERVICE_USER" -- "$@"
  elif command -v sudo >/dev/null 2>&1; then
    sudo -u "$SERVICE_USER" "$@"
  else
    err "Neither runuser nor sudo is available to run commands as $SERVICE_USER"
    exit 1
  fi
}

if ! id -u "$SERVICE_USER" >/dev/null 2>&1; then
  log "Creating system user: $SERVICE_USER"
  useradd --system --create-home --shell /bin/bash "$SERVICE_USER"
else
  log "Using existing user: $SERVICE_USER"
fi

log "Preparing install directory: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"

if [[ "$COPY_PROJECT" -eq 1 ]]; then
  if [[ "$PROJECT_ROOT" == "$INSTALL_DIR" ]]; then
    log "Project is already in install directory; skipping copy"
  else
    log "Copying project from $PROJECT_ROOT to $INSTALL_DIR"
    rsync -a \
      --exclude '.git/' \
      --exclude '.venv/' \
      --exclude '.pytest_cache/' \
      --exclude '__pycache__/' \
      --exclude 'storage/history.sqlite' \
      --exclude 'logs/*.log' \
      "$PROJECT_ROOT/" "$INSTALL_DIR/"
  fi
else
  log "Skipping project copy by request"
fi

log "Creating runtime directories"
mkdir -p "$INSTALL_DIR/logs" "$INSTALL_DIR/storage/recon" "$INSTALL_DIR/storage"
touch "$INSTALL_DIR/logs/system.log" "$INSTALL_DIR/logs/errors.log"
chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"

log "Creating/updating Python virtual environment"
if [[ ! -x "$INSTALL_DIR/.venv/bin/python" ]]; then
  run_as_user python3 -m venv "$INSTALL_DIR/.venv"
fi
run_as_user "$INSTALL_DIR/.venv/bin/python" -m pip install --upgrade pip
run_as_user "$INSTALL_DIR/.venv/bin/python" -m pip install -r "$INSTALL_DIR/requirements.txt"

ENV_FILE="$INSTALL_DIR/.env"
log "Creating/updating environment file: $ENV_FILE"
touch "$ENV_FILE"
chmod 600 "$ENV_FILE"
chown "$SERVICE_USER:$SERVICE_USER" "$ENV_FILE"

set_env_value() {
  local key="$1"
  local value="$2"
  local escaped
  escaped="$(printf '%s' "$value" | sed 's/[&/\\]/\\&/g')"
  if grep -qE "^${key}=" "$ENV_FILE"; then
    sed -i "s/^${key}=.*/${key}=${escaped}/" "$ENV_FILE"
  else
    printf '%s=%s\n' "$key" "$value" >> "$ENV_FILE"
  fi
}

set_env_value "RECON_ROOT" "$INSTALL_DIR"
if [[ -n "$TELEGRAM_TOKEN" ]]; then
  set_env_value "TELEGRAM_BOT_TOKEN" "$TELEGRAM_TOKEN"
elif ! grep -qE '^TELEGRAM_BOT_TOKEN=.+' "$ENV_FILE"; then
  log "WARNING: TELEGRAM_BOT_TOKEN was not provided. Add it to $ENV_FILE before starting the bot."
  if [[ "$START_SERVICES" -eq 1 ]]; then
    log "Disabling automatic start for this run because the bot token is missing."
    START_SERVICES=0
  fi
fi

write_service() {
  local service_name="$1"
  local description="$2"
  local module="$3"
  local service_path="/etc/systemd/system/${service_name}"

  log "Writing $service_path"
  cat > "$service_path" <<SERVICE
[Unit]
Description=${description}
After=network.target

[Service]
Type=simple
User=${SERVICE_USER}
WorkingDirectory=${INSTALL_DIR}
Environment=RECON_ROOT=${INSTALL_DIR}
EnvironmentFile=${ENV_FILE}
ExecStart=${INSTALL_DIR}/.venv/bin/python -m ${module}
Restart=always
RestartSec=5
StandardOutput=append:${INSTALL_DIR}/logs/system.log
StandardError=append:${INSTALL_DIR}/logs/errors.log

[Install]
WantedBy=multi-user.target
SERVICE
}

write_service "recon-bot.service" "Recon Core Telegram Bot" "bot.controller"
write_service "recon-worker.service" "Recon Core Worker" "runner.worker"

log "Reloading systemd"
systemctl daemon-reload

if [[ "$ENABLE_SERVICES" -eq 1 ]]; then
  log "Enabling services"
  systemctl enable recon-bot.service recon-worker.service
fi

if [[ "$START_SERVICES" -eq 1 ]]; then
  log "Starting/restarting services"
  systemctl restart recon-bot.service recon-worker.service
else
  log "Services installed but not started (--no-start)"
fi

log "Done"
log "Check status with: systemctl status recon-bot.service recon-worker.service"
log "Follow logs with: journalctl -u recon-bot.service -u recon-worker.service -f"
