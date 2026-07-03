# Grant Scout — инструкция для агента-установщика

> Ты — ИИ-агент, который помогает пользователю установить Grant Scout на его сервер.
> Пользователь не технический. Веди его за руку, шаг за шагом.
> Никогда не давай несколько шагов сразу — только один, жди подтверждения.

---

## Что такое Grant Scout

Это программа, которая автоматически ищет гранты для художников на десятках сайтов и присылает дайджест в Telegram. Устанавливается один раз, работает сама.

---

## Что тебе нужно знать заранее

- Репозиторий: `https://github.com/Saycastic/grant-scout` (приватный — нужен токен)
- Стек: Python 3.11+, SQLite, uv, systemd (или nohup как fallback)
- LLM backend: openclaw CLI (primary) или прямой Anthropic/OpenAI API (fallback)
- Единственное что нужно от пользователя: Telegram Bot Token + Chat ID

---

## Шаг 1 — Telegram Bot Token

Спроси пользователя:

> "Есть ли у тебя Telegram-бот? Если да — скинь его токен (выглядит как `1234567890:AAF...`). Если нет — напиши в Telegram [@BotFather](https://t.me/BotFather), отправь `/newbot`, придумай имя боту и скинь мне токен который он даст."

Когда получишь токен — сохрани его, переходи к шагу 2.

---

## Шаг 2 — Chat ID

Нужно узнать числовой ID чата пользователя. Два способа:

**Способ А — если агент сам является ботом пользователя:**
Chat ID уже известен из конфигурации агента. Используй его напрямую.

**Способ Б — внешний бот:**
1. Попроси пользователя написать своему боту любое слово (или /start)
2. Открой в браузере: `https://api.telegram.org/bot<TOKEN>/getUpdates`
3. Найди `"chat": {"id": XXXXXXXXX}` — это и есть Chat ID

Если `getUpdates` вернул `{"ok":true,"result":[]}` — бот не получил ни одного сообщения. Напомни пользователю написать боту что-нибудь, затем повтори запрос.

---

## Шаг 3 — Проверка сервера

Выполни на сервере:

```bash
python3 --version && git --version && echo "ok"
```

Ожидаемый результат: Python 3.10+ и git установлены.

Если python3 не найден:
```bash
apt-get update && apt-get install -y python3 python3-venv git curl
```

Проверь наличие uv (быстрый менеджер пакетов):
```bash
/root/.local/bin/uv --version 2>/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## Шаг 4 — Клонирование репозитория

```bash
cd /root
git clone https://github.com/Saycastic/grant-scout.git
cd grant-scout
```

Если репозиторий приватный и git просит пароль — используй GitHub токен:
```bash
git clone https://<GITHUB_TOKEN>@github.com/Saycastic/grant-scout.git
```

---

## Шаг 5 — Создание .env

В `.env` обязательны только два параметра — LLM Grant Scout определяет сам:

```bash
cat > /root/grant-scout/.env << EOF
TELEGRAM_BOT_TOKEN=<вставить токен из шага 1>
TELEGRAM_CHAT_ID=<вставить chat id из шага 2>
EOF
```

**Как Grant Scout выбирает LLM (автоматически, в порядке приоритета):**

1. `LLM_PROVIDER=openclaw` в `.env` → использует openclaw CLI
2. `LLM_API_KEY=...` в `.env` → прямой вызов Anthropic/OpenAI
3. **EXME / Agent Manager** → если на сервере есть `~/.agent-manager/.env` с ключами — подхватывает автоматически, включая gateway URL. Ничего дополнительно настраивать не нужно.
4. openclaw найден в PATH → использует его

Таким образом: если клиент на EXME — просто создаём `.env` с Telegram-данными и всё работает. Если на OpenClaw — тоже работает. Если ни то ни другое — нужен явный `LLM_API_KEY`.

---

## Шаг 6 — Запуск deploy.sh

```bash
cd /root/grant-scout && bash deploy.sh
```

Скрипт сделает сам:
- создаст виртуальное окружение Python
- установит зависимости
- инициализирует базу данных (24 источника грантов)
- запустит сервис через systemd (или nohup если systemd недоступен)

**Ожидаемый финал:**
```
[deploy] ✅ Grant Scout запущен!
```

Если видишь ошибку — смотри раздел "Типичные проблемы" ниже.

---

## Шаг 7 — Первый тест

Запусти немедленную проверку и отправь дайджест:

```bash
cd /root/grant-scout && PYTHONPATH=. .venv/bin/python3 -c "
import os
from pathlib import Path
for line in Path('.env').read_text().splitlines():
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, _, v = line.partition('=')
        os.environ[k.strip()] = v.strip()

from src.crawler.runner import run_crawler
from src.extractor.pipeline import run_extractor
from src.delivery.telegram import send_digest

print('Crawling...')
run_crawler()
print('Extracting...')
run_extractor()
print('Sending...')
send_digest()
print('Done.')
" 2>&1
```

Пользователь должен получить сообщение в Telegram с грантами.

Скажи пользователю: *"Проверь Telegram — должны прийти сообщения с грантами для художников."*

---

## Расписание (автоматически)

После установки Grant Scout работает сам по расписанию:
- **Ежедневно** — краулит агрегаторы (ArtDeadline, NYFA, Submittable)
- **Еженедельно** — краулит прямые фонды (FCA, Artadia, MacDowell и др.)
- **По понедельникам в 09:00** — отправляет дайджест новых грантов
- **По пятницам** — напоминает о грантах с истекающими дедлайнами

---

## Команды для пользователя

Объясни пользователю что он может писать своему агенту:

| Что сказать агенту | Что произойдёт |
|---|---|
| "запусти гранты" | Полный прогон + дайджест в Telegram |
| "статус grant scout" | Сколько грантов в БД, последний краулинг |
| "пришли дайджест грантов" | Отправит всё что есть в БД |

---

## Типичные проблемы

### `No module named 'src'`
PYTHONPATH не задан. Всегда запускай с префиксом:
```bash
cd /root/grant-scout && PYTHONPATH=. .venv/bin/python3 ...
```

### `openclaw: No such file or directory` / LLM errors
Grant Scout сам пробует найти LLM: сначала openclaw, потом EXME/Agent Manager ключи в `~/.agent-manager/.env`, потом явный `LLM_API_KEY` в `.env`.

Если всё равно ошибка — добавь в `.env`:
```
LLM_API_KEY=sk-ant-...
LLM_PROVIDER=anthropic
```

### `Failed to connect to bus` (systemd)
Сервер работает в контейнере без systemd. deploy.sh автоматически использует nohup — это нормально.

### `uv: command not found`
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
```

### Бот не отправляет сообщения
Проверь что `TELEGRAM_BOT_TOKEN` и `TELEGRAM_CHAT_ID` правильно вписаны в `.env`. Chat ID — это число, не username.

### 14 ошибок краулера при первом запуске
Часть источников может быть недоступна (404, таймаут, JS-рендеринг). Это нормально — агрегаторы (ArtDeadline, Submittable) работают стабильно и дают основной поток грантов. Ошибочные источники алертят в Telegram.

---

## Обновление

```bash
cd /root/grant-scout && bash update.sh
```

Скрипт сделает `git pull` и перезапустит сервис.

---

## Структура проекта (для справки)

```
/root/grant-scout/
├── src/
│   ├── main.py              # Планировщик
│   ├── crawler/             # Краулер (HTML + JS через Playwright)
│   ├── extractor/           # LLM-нормализатор грантов
│   ├── delivery/            # Отправка в Telegram
│   ├── alerts/              # Алерты при ошибках
│   └── database/            # SQLite + 24 источника
├── deploy.sh                # Установка
├── update.sh                # Обновление
├── .env                     # Токены (не в git)
└── data/grant_scout.db      # База данных грантов
```
