#!/bin/bash
# ═══════════════════════════════════════════════════════════════
#  Grant Scout — One-line installer
#  Usage: bash install.sh
# ═══════════════════════════════════════════════════════════════

set -e

REPO_URL="https://github.com/Saycastic/grant-scout"
INSTALL_DIR="/opt/grant-scout"
SERVICE_NAME="grant-scout"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info()    { echo -e "${CYAN}[•]${NC} $1"; }
success() { echo -e "${GREEN}[✓]${NC} $1"; }
warn()    { echo -e "${YELLOW}[!]${NC} $1"; }
error()   { echo -e "${RED}[✗]${NC} $1"; exit 1; }
section() { echo -e "\n${BOLD}$1${NC}"; }

# ── Root check ────────────────────────────────────────────────
if [ "$EUID" -ne 0 ]; then
  error "Please run as root: sudo bash install.sh"
fi

echo -e "${BOLD}"
echo "  ╔════════════════════════════════════╗"
echo "  ║       Grant Scout Installer        ║"
echo "  ║  Art grants monitor for artists    ║"
echo "  ╚════════════════════════════════════╝"
echo -e "${NC}"

# ── System dependencies ───────────────────────────────────────
section "1/6  System dependencies"

apt-get update -qq
apt-get install -y -qq python3 python3-pip curl git wget unzip 2>/dev/null

# Install uv
if ! command -v uv &>/dev/null && [ ! -f "/root/.local/bin/uv" ]; then
  info "Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi
UV=$(command -v uv 2>/dev/null || echo "/root/.local/bin/uv")
success "Dependencies ready"

# Install Playwright system deps (for JS crawling)
info "Installing Playwright system deps..."
apt-get install -y -qq \
  libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
  libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 \
  libxfixes3 libxrandr2 libgbm1 libasound2 libpango-1.0-0 \
  libcairo2 libgtk-3-0 2>/dev/null || true
success "System deps ready"

# ── Clone repo ────────────────────────────────────────────────
section "2/6  Cloning Grant Scout"

if [ -d "$INSTALL_DIR" ]; then
  warn "Directory $INSTALL_DIR already exists — pulling latest..."
  cd "$INSTALL_DIR" && git pull origin main
else
  git clone "$REPO_URL" "$INSTALL_DIR"
fi
cd "$INSTALL_DIR"
success "Repository ready at $INSTALL_DIR"

# ── Python venv ───────────────────────────────────────────────
section "3/6  Python environment"

$UV venv .venv --python 3.11 2>/dev/null || $UV venv .venv
$UV pip install --python .venv/bin/python3 -r requirements.txt
.venv/bin/python3 -m playwright install chromium 2>/dev/null || true
success "Python environment ready"

# ── Configuration ─────────────────────────────────────────────
section "4/6  Configuration"

if [ -f ".env" ]; then
  warn ".env already exists — skipping (edit manually if needed)"
else
  echo ""
  echo -e "${BOLD}Please provide the following:${NC}"
  echo ""

  read -rp "  Telegram Bot Token (from @BotFather): " TG_TOKEN
  read -rp "  Your Telegram Chat ID (your user ID): " TG_CHAT_ID
  echo ""
  echo -e "  LLM Provider — choose one:"
  echo -e "  ${CYAN}1${NC}) Anthropic (Claude)"
  echo -e "  ${CYAN}2${NC}) OpenAI (GPT)"
  echo -e "  ${CYAN}3${NC}) Custom OpenAI-compatible endpoint"
  read -rp "  Choice [1/2/3]: " LLM_CHOICE

  case $LLM_CHOICE in
    1)
      read -rp "  Anthropic API key: " LLM_KEY
      LLM_PROVIDER="anthropic"
      LLM_MODEL="claude-haiku-4-5"
      LLM_BASE_URL=""
      ;;
    2)
      read -rp "  OpenAI API key: " LLM_KEY
      LLM_PROVIDER="openai"
      LLM_MODEL="gpt-4o-mini"
      LLM_BASE_URL=""
      ;;
    3)
      read -rp "  API key: " LLM_KEY
      read -rp "  Base URL (e.g. https://llm.example.com/openai/v1): " LLM_BASE_URL
      read -rp "  Model name: " LLM_MODEL
      LLM_PROVIDER="custom"
      ;;
    *)
      warn "Invalid choice — using OpenAI by default"
      read -rp "  OpenAI API key: " LLM_KEY
      LLM_PROVIDER="openai"
      LLM_MODEL="gpt-4o-mini"
      LLM_BASE_URL=""
      ;;
  esac

  cat > .env <<EOF
# Telegram
TELEGRAM_BOT_TOKEN=${TG_TOKEN}
TELEGRAM_CHAT_ID=${TG_CHAT_ID}

# LLM
LLM_PROVIDER=${LLM_PROVIDER}
LLM_API_KEY=${LLM_KEY}
LLM_MODEL=${LLM_MODEL}
EOF

  if [ -n "$LLM_BASE_URL" ]; then
    echo "LLM_BASE_URL=${LLM_BASE_URL}" >> .env
  fi

  chmod 600 .env
  success ".env created"
fi

# ── Database ──────────────────────────────────────────────────
section "5/6  Database setup"

mkdir -p data/backups/daily
PYTHONPATH="$INSTALL_DIR" .venv/bin/python3 -m src.database.seed_sources
success "Database initialised with $(PYTHONPATH=$INSTALL_DIR .venv/bin/python3 -c "
from src.database.db import get_conn
print(get_conn().execute('SELECT COUNT(*) FROM sources WHERE status=\'active\'').fetchone()[0])
" 2>/dev/null) sources"

# ── Systemd service ───────────────────────────────────────────
section "6/6  Systemd service"

cat > /etc/systemd/system/${SERVICE_NAME}.service <<EOF
[Unit]
Description=Grant Scout — art grants monitor
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=${INSTALL_DIR}
Environment=PYTHONPATH=${INSTALL_DIR}
EnvironmentFile=${INSTALL_DIR}/.env
ExecStart=${INSTALL_DIR}/.venv/bin/python3 ${INSTALL_DIR}/src/main.py
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "${SERVICE_NAME}"
systemctl restart "${SERVICE_NAME}"
sleep 3

if systemctl is-active --quiet "${SERVICE_NAME}"; then
  success "Service ${SERVICE_NAME} is running"
else
  error "Service failed to start. Check: journalctl -u ${SERVICE_NAME} -n 50"
fi

# ── Done ──────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}════════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD}  Grant Scout installed successfully! 🎨${NC}"
echo -e "${GREEN}${BOLD}════════════════════════════════════════${NC}"
echo ""
echo -e "  Useful commands:"
echo -e "  ${CYAN}systemctl status grant-scout${NC}       — check status"
echo -e "  ${CYAN}journalctl -u grant-scout -f${NC}       — live logs"
echo -e "  ${CYAN}systemctl restart grant-scout${NC}      — restart"
echo -e "  ${CYAN}nano ${INSTALL_DIR}/.env${NC}           — edit config"
echo ""
echo -e "  Repo: ${CYAN}https://github.com/Saycastic/grant-scout${NC}"
echo ""
