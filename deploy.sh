#!/bin/bash
# Grant Scout — deploy script
# Запуск: bash deploy.sh
# Требования: git, python3, openclaw на хосте

set -e

REPO_DIR="$HOME/grant-scout"
SERVICE_NAME="grant-scout"
VENV="$REPO_DIR/.venv"
PYTHON="$VENV/bin/python3"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${GREEN}[deploy]${NC} $1"; }
warn()  { echo -e "${YELLOW}[warn]${NC} $1"; }
error() { echo -e "${RED}[error]${NC} $1"; exit 1; }

# ── 1. Зависимости ─────────────────────────────────────────────────────────────
info "Checking dependencies..."
command -v python3 >/dev/null || error "python3 not found"
command -v openclaw >/dev/null || warn "openclaw not in PATH — set OPENCLAW_BIN in .env"
command -v git >/dev/null || error "git not found"

# ── 2. Виртуальное окружение ───────────────────────────────────────────────────
if [ ! -f "$VENV/bin/python3" ]; then
    info "Creating virtualenv..."
    python3 -m venv "$VENV"
fi

info "Installing Python dependencies..."
# Используем uv если есть (быстрее), иначе pip
if command -v uv >/dev/null 2>&1; then
    uv pip install --python "$PYTHON" -r "$REPO_DIR/requirements.txt" -q
else
    "$VENV/bin/pip" install -q -r "$REPO_DIR/requirements.txt"
fi

# ── 3. .env ────────────────────────────────────────────────────────────────────
if [ ! -f "$REPO_DIR/.env" ]; then
    cp "$REPO_DIR/.env.example" "$REPO_DIR/.env"
    warn ".env не найден — создан из .env.example"
    warn "Открой $REPO_DIR/.env и впиши TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID"
    warn "Затем запусти deploy.sh снова"
    exit 0
fi

# Проверяем что токен вписан
source "$REPO_DIR/.env"
if [ "$TELEGRAM_BOT_TOKEN" = "your_bot_token_here" ] || [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    error "TELEGRAM_BOT_TOKEN не задан в .env"
fi
if [ "$TELEGRAM_CHAT_ID" = "your_chat_id_here" ] || [ -z "$TELEGRAM_CHAT_ID" ]; then
    error "TELEGRAM_CHAT_ID не задан в .env"
fi

# ── 4. База данных ─────────────────────────────────────────────────────────────
info "Initialising database..."
cd "$REPO_DIR"
PYTHONPATH="$REPO_DIR" "$PYTHON" -m src.database.db
PYTHONPATH="$REPO_DIR" "$PYTHON" -m src.database.seed_sources

# ── 5. Systemd unit ────────────────────────────────────────────────────────────
info "Installing systemd service..."

# Читаем .env в формате для systemd (EnvironmentFile требует KEY=VALUE без export)
ENV_FILE="$REPO_DIR/.env"

cat > /tmp/grant-scout.service << EOF
[Unit]
Description=Grant Scout — art grants monitor
After=network.target
Wants=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$REPO_DIR
EnvironmentFile=$ENV_FILE
Environment=PYTHONPATH=$REPO_DIR
ExecStart=$PYTHON src/main.py
Restart=on-failure
RestartSec=30
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
EOF

# User-level systemd (не требует sudo)
mkdir -p "$HOME/.config/systemd/user"
cp /tmp/grant-scout.service "$HOME/.config/systemd/user/$SERVICE_NAME.service"

systemctl --user daemon-reload
systemctl --user enable "$SERVICE_NAME"
systemctl --user restart "$SERVICE_NAME"

# ── 6. Проверка ────────────────────────────────────────────────────────────────
sleep 3
STATUS=$(systemctl --user is-active "$SERVICE_NAME" 2>/dev/null || echo "unknown")

if [ "$STATUS" = "active" ]; then
    info "✅ Grant Scout запущен и работает!"
    info "Логи: journalctl --user -u $SERVICE_NAME -f"
    info "Стоп: systemctl --user stop $SERVICE_NAME"
    info "Рестарт: systemctl --user restart $SERVICE_NAME"
else
    warn "Сервис запущен, но статус: $STATUS"
    warn "Проверь логи: journalctl --user -u $SERVICE_NAME -n 50"
fi
