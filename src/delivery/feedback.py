"""
Telegram Feedback — inline кнопки под грантами (👍 / 💾 / 👎).
Обрабатывает callback_query от Telegram.
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx

from src.database.db import get_conn

# Load .env
_env_path = Path(__file__).parent.parent.parent / ".env"
if _env_path.exists():
    for _line in _env_path.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())


def _bot_token() -> str:
    return os.environ.get("TELEGRAM_BOT_TOKEN", "")


def make_feedback_keyboard(opp_id: int) -> dict:
    """Возвращает inline keyboard для одного гранта."""
    return {
        "inline_keyboard": [[
            {"text": "👍 Useful", "callback_data": f"fb:{opp_id}:useful"},
            {"text": "💾 Save", "callback_data": f"fb:{opp_id}:saved"},
            {"text": "👎 Not relevant", "callback_data": f"fb:{opp_id}:not_relevant"},
        ]]
    }


def send_with_feedback(chat_id: str, text: str, opp_id: int) -> Optional[int]:
    """Отправляет сообщение с inline кнопками фидбека."""
    token = _bot_token()
    if not token:
        print(text)
        return None

    try:
        resp = httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "reply_markup": make_feedback_keyboard(opp_id),
                "disable_web_page_preview": False,
            },
            timeout=15,
        )
        data = resp.json()
        if data.get("ok"):
            return data["result"]["message_id"]
        else:
            print(f"[feedback] Telegram error: {data.get('description')}")
            return None
    except Exception as e:
        print(f"[feedback] Send error: {e}")
        return None


def handle_callback(callback_query: dict):
    """
    Обрабатывает нажатие кнопки фидбека.
    Вызывается из webhook или polling loop.
    """
    token = _bot_token()
    cq_id = callback_query.get("id")
    data = callback_query.get("data", "")
    user = callback_query.get("from", {})
    user_id = str(user.get("id", ""))

    # Парсим callback_data: "fb:<opp_id>:<label>"
    parts = data.split(":")
    if len(parts) != 3 or parts[0] != "fb":
        return

    opp_id = int(parts[1])
    label = parts[2]

    # Сохраняем фидбек
    conn = get_conn()
    conn.execute("""
        INSERT OR REPLACE INTO opportunity_feedback (opportunity_id, user_id, label, created_at)
        VALUES (?, ?, ?, ?)
    """, (opp_id, user_id, label, datetime.utcnow().isoformat()))
    conn.commit()

    # Если saved — добавляем пометку в opportunities
    if label == "saved":
        conn.execute("UPDATE opportunities SET sent_at = sent_at WHERE id = ?", (opp_id,))

    conn.close()

    # Отвечаем Telegram (убираем спиннер)
    LABELS = {
        "useful": "👍 Marked as useful",
        "saved": "💾 Saved",
        "not_relevant": "👎 Marked as not relevant",
    }
    answer = LABELS.get(label, "✓")
    if token and cq_id:
        try:
            httpx.post(
                f"https://api.telegram.org/bot{token}/answerCallbackQuery",
                json={"callback_query_id": cq_id, "text": answer},
                timeout=5,
            )
        except Exception:
            pass

    print(f"[feedback] opp {opp_id}: {label} from user {user_id}")


def run_polling(timeout: int = 30):
    """
    Простой polling loop для обработки callback queries.
    Запускать отдельным процессом: python -m src.delivery.feedback
    """
    token = _bot_token()
    if not token:
        print("[feedback] No bot token, polling disabled")
        return

    offset = 0
    print("[feedback] Starting polling...")

    while True:
        try:
            resp = httpx.get(
                f"https://api.telegram.org/bot{token}/getUpdates",
                params={"offset": offset, "timeout": timeout, "allowed_updates": ["callback_query"]},
                timeout=timeout + 5,
            )
            updates = resp.json().get("result", [])
            for update in updates:
                offset = update["update_id"] + 1
                if "callback_query" in update:
                    handle_callback(update["callback_query"])
        except Exception as e:
            print(f"[feedback] Polling error: {e}")
            import time; time.sleep(5)


# Optional import guard
try:
    from typing import Optional
except ImportError:
    pass


if __name__ == "__main__":
    run_polling()
