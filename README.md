# Grant Scout

Агент для мониторинга грантов для современных визуальных художников.

## Быстрый старт (Docker)

```bash
git clone <repo>
cd grant-scout
cp config/config.example.yml config/config.yml
# Вписать TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID в config.yml
docker compose up -d
```

## Структура

```
src/
  crawler/      — fetcher: httpx + Playwright
  extractor/    — LLM-нормализатор → JSON схема гранта
  database/     — SQLite: schema, db.py, seed_sources.py
  delivery/     — Telegram digest
  alerts/       — алерты при падении краулера
config/         — config.yml (из example)
data/           — grant_scout.db (создаётся автоматически)
scripts/        — запуск краулера вручную
```

## Добавление нового источника

Добавить запись в `src/database/seed_sources.py` → запустить `python -m src.database.seed_sources`.
