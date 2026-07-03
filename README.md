# 🎨 Grant Scout

Autonomous agent that monitors art grant opportunities worldwide and delivers a curated digest to Telegram.

**Built for visual artists** — painting, sculpture, installation, video art, performance. Not photography, design, or film.

---

## Agent Installation Instructions

> **This README is written for an AI agent.** If a user asks you to install Grant Scout — follow the steps below exactly, in order, without skipping anything.

---

### Step 1 — Ask the user for required parameters

Before doing anything else, ask the user for these three things in chat:

1. **Telegram Bot Token** — they get it from [@BotFather](https://t.me/BotFather)
2. **Telegram Chat ID** — they can find it via [@userinfobot](https://t.me/userinfobot)
3. **LLM API key** — Anthropic, OpenAI, or a custom endpoint key

Do not proceed until you have all three.

---

### Step 2 — Clone the repository

```bash
git clone https://github.com/Saycastic/grant-scout /opt/grant-scout
```

---

### Step 3 — Run the installer with parameters via stdin

Pass the parameters directly to `install.sh` through stdin — do not run it interactively:

```bash
printf "TOKEN\nCHAT_ID\n3\nAPI_KEY\nhttps://llm.exme.ae/openai/v1\ngpt-4o-mini\n" | bash /opt/grant-scout/install.sh
```

Replace:
- `TOKEN` — Telegram Bot Token from Step 1
- `CHAT_ID` — Telegram Chat ID from Step 1
- `3` — selects "Custom endpoint" in the LLM menu (use this for EXME gateway)
- `API_KEY` — LLM API key from Step 1
- `https://llm.exme.ae/openai/v1` — EXME gateway base URL
- `gpt-4o-mini` — model name

If the user has an Anthropic key (Claude), use choice `1` instead:
```bash
printf "TOKEN\nCHAT_ID\n1\nAPI_KEY\n" | bash /opt/grant-scout/install.sh
```

If the user has an OpenAI key (GPT), use choice `2`:
```bash
printf "TOKEN\nCHAT_ID\n2\nAPI_KEY\n" | bash /opt/grant-scout/install.sh
```

---

### Step 4 — Verify the service is running

```bash
systemctl is-active grant-scout
```

Expected output: `active`

If not active, check logs:
```bash
journalctl -u grant-scout -n 50 --no-pager
```

---

### Step 5 — Send a test digest

Confirm everything works end-to-end by triggering a manual digest:

```bash
cd /opt/grant-scout && PYTHONPATH=/opt/grant-scout .venv/bin/python3 -c "
from src.delivery.telegram import send_digest
send_digest(force=True)
"
```

The user should receive grant messages in Telegram. If they do — installation is complete.

---

## Useful commands (post-install)

```bash
systemctl status grant-scout           # check status
journalctl -u grant-scout -f           # live logs
systemctl restart grant-scout          # restart

# Run full pipeline manually
cd /opt/grant-scout && PYTHONPATH=/opt/grant-scout .venv/bin/python3 -c "
from src.crawler.runner import run_crawler
from src.extractor.pipeline import run_extractor
from src.delivery.telegram import send_digest
run_crawler('daily')
run_extractor()
send_digest()
"
```

---

## What it does

- Crawls **73+ sources** — foundations, arts councils, aggregators across Europe, North America, Asia, MENA, Latin America
- Extracts and normalises grant info via LLM — name, deadline, amount, eligibility, link
- Deduplicates, filters expired grants, sends digest to Telegram
- Runs on a schedule: daily crawl + weekly digest

## Sources coverage

| Region | Sources |
|--------|---------|
| Europe | 21 |
| USA | 15 |
| Asia | 14 |
| International | 13 |
| Canada | 6 |
| MENA | 4 |
| Latin America | 1 |

---

## License

MIT
