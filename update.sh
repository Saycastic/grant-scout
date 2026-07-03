#!/bin/bash
# Обновление Grant Scout с GitHub
# Запуск: bash update.sh

set -e
REPO_DIR="$HOME/grant-scout"
SERVICE_NAME="grant-scout"
VENV="$REPO_DIR/.venv"
PYTHON="$VENV/bin/python3"

GREEN='\033[0;32m'
NC='\033[0m'
info() { echo -e "${GREEN}[update]${NC} $1"; }

info "Pulling latest changes..."
cd "$REPO_DIR"
git pull

info "Updating dependencies..."
if command -v uv >/dev/null 2>&1; then
    uv pip install --python "$PYTHON" -r requirements.txt -q
else
    "$VENV/bin/pip" install -q -r requirements.txt
fi

info "Running migrations..."
PYTHONPATH="$REPO_DIR" "$PYTHON" -m src.database.db
PYTHONPATH="$REPO_DIR" "$PYTHON" -m src.database.seed_sources

info "Restarting service..."
systemctl --user restart "$SERVICE_NAME"

sleep 2
systemctl --user status "$SERVICE_NAME" --no-pager | head -5
info "Done."
