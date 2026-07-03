# Grant Scout 🎨

Агент для мониторинга грантов для современных визуальных художников.
Краулит сайты фондов, извлекает гранты через OpenClaw, шлёт дайджест в Telegram.

---

## Установка (5 минут)

### 1. Клонировать репозиторий

```bash
git clone <repo_url> ~/grant-scout
cd ~/grant-scout
```

### 2. Создать Telegram-бота

1. Напиши [@BotFather](https://t.me/BotFather) → `/newbot`
2. Скопируй **токен** (выглядит как `123456789:AAF...`)
3. Напиши своему боту `/start`
4. Узнай свой chat_id: напиши [@userinfobot](https://t.me/userinfobot)

### 3. Запустить деплой

```bash
bash deploy.sh
```

Скрипт создаст `.env` из шаблона и попросит вписать токены.
После заполнения запусти ещё раз:

```bash
nano .env       # вписать TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID
bash deploy.sh  # запустить снова
```

Готово. Агент работает в фоне и сам перезапускается при сбоях.

---

## Управление

```bash
# Логи в реальном времени
journalctl --user -u grant-scout -f

# Статус
systemctl --user status grant-scout

# Остановить
systemctl --user stop grant-scout

# Перезапустить
systemctl --user restart grant-scout

# Обновить до последней версии
bash update.sh
```

---

## Расписание

| Что               | Когда                        |
|-------------------|------------------------------|
| Краулинг (daily)  | Ежедневно в 06:00 UTC        |
| Краулинг (weekly) | По понедельникам в 05:00 UTC |
| Дайджест новых    | По понедельникам в 09:00 UTC |
| Истекающие дедл.  | По пятницам в 09:00 UTC      |

---

## Структура проекта

```
src/
  crawler/        — httpx + Playwright fetcher
  extractor/      — LLM-нормализатор (через openclaw agent)
  database/       — SQLite: схема, инициализация, источники
  delivery/       — Telegram-дайджест
  alerts/         — алерты при ошибках краулера
  main.py         — scheduler
config/           — конфиг-шаблон
data/             — grant_scout.db (создаётся автоматически)
deploy.sh         — установка и запуск
update.sh         — обновление
```

---

## Добавление нового источника

Добавь запись в `src/database/seed_sources.py` — затем:

```bash
bash update.sh
```

---

## Что требуется на сервере

- Python 3.10+
- OpenClaw (уже установлен и настроен)
- systemd (стандартный в Ubuntu/Debian/CentOS)
