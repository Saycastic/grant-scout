# Grant Scout — Project State Reference

Last updated: 2026-07-03

## Repo
- GitHub: https://github.com/Saycastic/grant-scout (private)
- Branch: main, 8 commits
- Remote configured with token in `/root/grant-scout/.env` as `GITHUB_TOKEN`

## Server
- Location: `/root/grant-scout/` on Agent Manager dev VPS
- Python venv: `/root/grant-scout/.venv/` (Python 3.11 via uv)
- DB: `/root/grant-scout/data/grant_scout.db` (SQLite)
- Process: running via nohup (no systemd — container environment)
- Logs: `tail -f /root/grant-scout/data/grant-scout.log`
- Stop: `pkill -f src/main.py`

## .env contents (structure)
```
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=410378918
GITHUB_TOKEN=...
ANTHROPIC_API_KEY=...   # auto-loaded from ~/.agent-manager/.env if absent
ANTHROPIC_BASE_URL=...  # EXME gateway
LLM_PROVIDER=anthropic
LLM_MODEL=claude-haiku-4-5
```

## Source Registry — 25 sources
Parser types: `html` (static), `dynamic_js` (Playwright)

### Confirmed working HTML sources
| source_id | URL | Status |
|---|---|---|
| sustainable_arts | sustainableartsfoundation.org/awards | ✅ |
| fca_emergency | foundationforcontemporaryarts.org/grants/emergency-grants/ | ✅ |
| fca_application | foundationforcontemporaryarts.org/grants/by-application/ | ✅ |
| artdeadline | artdeadline.com/?type=Grant | ✅ |

### Confirmed working JS sources (Playwright)
| source_id | URL | Grants found | Notes |
|---|---|---|---|
| pollock_krasner | pkf.org/apply/ | 4 | high quality |
| creative_capital | creative-capital.org/ | 2 | homepage, not /apply/ |
| nyfa_opportunities | nyfa.org/opportunities/?discipline=Visual+Arts&type=Grant | 0 | content behind auth wall |

### Known broken sources (404 / timeout)
- `jerome_fnd` — HTTP -1 (timeout)
- `british_council_arts` — HTTP 0
- `goethe_fnd` — HTTP 404
- `pro_helvetia` — HTTP 404
- `creative_capital` (old URL /apply/) — was 404, fixed to /

## Architecture
```
Source Registry (SQLite sources table)
    ↓
Crawler (html_fetcher.py / js_fetcher.py)
    ↓ raw_pages table
Extractor + LLM (llm_normalizer.py → pipeline.py)
    ↓ opportunities table
Telegram Digest (delivery/telegram.py)
```

## LLM Backend Auto-detection Order
1. `LLM_PROVIDER=openclaw` in .env → openclaw CLI
2. `LLM_API_KEY` in .env → direct Anthropic/OpenAI
3. `~/.agent-manager/.env` with ANTHROPIC_API_KEY → EXME gateway (auto, no config needed)
4. openclaw binary in PATH → openclaw CLI

## Key Files
```
src/extractor/llm_normalizer.py   # _detect_llm_config() — auto LLM backend
src/extractor/pipeline.py         # field aliases: name/funder/website → title/org/url
src/crawler/js_fetcher.py         # Playwright, --no-sandbox, domcontentloaded + scroll
src/crawler/runner.py             # dispatcher html/js per source parser_type
src/delivery/telegram.py          # HTML parse_mode, auto-split >3800 chars
deploy.sh                         # uv-aware, systemd + nohup fallback
DEPLOY_FOR_AGENT.md               # Onboarding guide written FOR an AI agent installer
```

## Telegram
- chat_id: 410378918
- parse_mode: HTML (not Markdown)
- Auto-splits messages at 3800 chars
- Digest icons: 🟢 high, 🟡 medium, 🔴 low

## Remaining Work
- [ ] `deploy.sh` — add `playwright install chromium` + `playwright install-deps chromium`
- [ ] Fix broken sources (jerome, british_council, goethe, pro_helvetia) — update URLs
- [ ] NYFA — needs auth or different URL to get actual grant listings
- [ ] Test full 25-source crawl after URL fixes
- [ ] Expiring deadlines digest (Friday alerts)
