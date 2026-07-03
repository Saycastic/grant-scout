# 🎨 Grant Scout

An autonomous agent that monitors art grant opportunities worldwide and delivers a curated digest to your Telegram.

**Built for visual artists** — painting, sculpture, installation, video art, performance. Not photography, design, or film.

---

## What it does

- Crawls **73+ sources** — foundations, national arts councils, aggregators across Europe, North America, Asia, MENA, Latin America
- Extracts and normalises grant info using LLM — name, deadline, amount, eligibility, link
- Deduplicates so you never get the same grant twice
- Sends each grant as a Telegram message with 👍 / 💾 / 👎 feedback buttons
- Runs on a schedule: daily crawl + weekly digest

---

## Requirements

- Linux VPS (Ubuntu 22.04+ recommended), 1GB+ RAM
- A Telegram bot token — create one via [@BotFather](https://t.me/BotFather)
- Your Telegram user ID (use [@userinfobot](https://t.me/userinfobot) to find it)
- An LLM API key — Anthropic (Claude) or OpenAI (GPT)

---

## Install

```bash
git clone https://github.com/Saycastic/grant-scout
cd grant-scout
sudo bash install.sh
```

The installer will:
1. Install system dependencies + Python env
2. Ask for your Telegram token, chat ID, and LLM key
3. Initialise the database with all sources
4. Deploy and start the systemd service

---

## Configuration

All config lives in `/opt/grant-scout/.env`:

```env
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# LLM
LLM_PROVIDER=anthropic          # anthropic | openai | custom
LLM_API_KEY=your_api_key_here
LLM_MODEL=claude-haiku-4-5
# LLM_BASE_URL=https://...      # only for custom endpoints
```

After editing `.env`, restart the service:
```bash
systemctl restart grant-scout
```

---

## Useful commands

```bash
systemctl status grant-scout        # check if running
journalctl -u grant-scout -f        # live logs
systemctl restart grant-scout       # restart
systemctl stop grant-scout          # stop
```

---

## Sources coverage

| Region | Sources |
|--------|---------|
| Europe | 21 |
| USA | 15 |
| Asia | 14 |
| International | 13 |
| North America (Canada) | 6 |
| MENA | 4 |
| Latin America | 1 |

---

## Adding new sources

Edit `src/database/seed_sources.py` and add an entry to the `SOURCES` list, then:

```bash
cd /opt/grant-scout
PYTHONPATH=/opt/grant-scout .venv/bin/python3 -m src.database.seed_sources
systemctl restart grant-scout
```

---

## License

MIT
