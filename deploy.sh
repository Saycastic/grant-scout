#!/bin/bash
# Grant Scout — deploy script
# Запуск: bash deploy.sh
# Требования: git, python3, openclaw на хосте

set -e

REPO_DIR="/root/grant-scout"
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
    if command -v uv >/dev/null 2>&1; then
        uv venv "$VENV" --python 3.11
    else
        python3 -m venv "$VENV"
    fi
fi

info "Installing Python dependencies..."
UV_BIN=$(command -v uv 2>/dev/null || echo "/root/.local/bin/uv")
if [ -f "$UV_BIN" ]; then
    "$UV_BIN" pip install --python "$PYTHON" -r "$REPO_DIR/requirements.txt" -q
elif [ -f "$VENV/bin/pip" ]; then
    "$VENV/bin/pip" install -q -r "$REPO_DIR/requirements.txt"
else
    error "Neither uv nor pip found. Cannot install dependencies."
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

# ── 5. Запуск ──────────────────────────────────────────────────────────────────
info "Starting Grant Scout..."

# Пробуем systemd (работает на полноценном VPS)
if systemctl --user daemon-reload 2>/dev/null; then
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
    mkdir -p "$HOME/.config/systemd/user"
    cp /tmp/grant-scout.service "$HOME/.config/systemd/user/$SERVICE_NAME.service"
    systemctl --user daemon-reload
    systemctl --user enable "$SERVICE_NAME"
    systemctl --user restart "$SERVICE_NAME"
    sleep 3
    STATUS=$(systemctl --user is-active "$SERVICE_NAME" 2>/dev/null || echo "unknown")
    if [ "$STATUS" = "active" ]; then
        info "✅ Grant Scout запущен через systemd!"
        info "Логи: journalctl --user -u $SERVICE_NAME -f"
    else
        warn "Systemd статус: $STATUS — проверь логи: journalctl --user -u $SERVICE_NAME -n 50"
    fi
else
    # Fallback: nohup (для контейнеров без systemd)
    pkill -f "src/main.py" 2>/dev/null || true
    cd "$REPO_DIR"
    nohup env PYTHONPATH="$REPO_DIR" "$PYTHON" "$REPO_DIR/src/main.py" >> "$REPO_DIR/data/grant-scout.log" 2>&1 &
    sleep 2
    if pgrep -f "src/main.py" > /dev/null; then
        info "✅ Grant Scout запущен (nohup, PID $(pgrep -f 'src/main.py'))!"
        info "Логи: tail -f $REPO_DIR/data/grant-scout.log"
        info "Стоп: pkill -f src/main.py"
    else
        warn "Что-то пошло не так. Проверь логи: tail -20 $REPO_DIR/data/grant-scout.log"
    fi
fi
