"""
Telegram Delivery — форматирует и отправляет дайджест грантов.
"""

import os
import json
import httpx
from datetime import datetime, date, timedelta
from typing import Optional

from src.database.db import get_conn


def _bot_token() -> str:
    return os.environ.get("TELEGRAM_BOT_TOKEN", "")


def _chat_id() -> str:
    return os.environ.get("TELEGRAM_CHAT_ID", "")


def send_message(text: str, parse_mode: str = "HTML") -> Optional[int]:
    """Отправляет сообщение в Telegram. Возвращает message_id или None."""
    token = _bot_token()
    chat_id = _chat_id()
    if not token or not chat_id:
        print(f"[delivery] No Telegram config — printing to stdout:\n{text}\n")
        return None

    try:
        resp = httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True,
            },
            timeout=15,
        )
        data = resp.json()
        if data.get("ok"):
            return data["result"]["message_id"]
        else:
            print(f"[delivery] Telegram error: {data}")
            return None
    except Exception as e:
        print(f"[delivery] Send error: {e}")
        return None


def format_opportunity(opp: dict, idx: int) -> str:
    """Форматирует одну возможность в HTML-блок."""
    quality_icon = {
        "high": "🟢",
        "medium": "🟡",
        "low": "🟠",
    }.get(opp.get("opportunity_quality", ""), "⚪")

    lines = []

    # Заголовок
    title = opp.get("title", "Без названия")
    url = opp.get("url", "")
    if url:
        lines.append(f'{quality_icon} <b><a href="{url}">{title}</a></b>')
    else:
        lines.append(f"{quality_icon} <b>{title}</b>")

    # Организация
    org = opp.get("organization", "")
    if org:
        lines.append(f"🏛 {org}")

    # Сумма
    amount = opp.get("amount", "")
    if amount:
        lines.append(f"💰 {amount}")

    # Дедлайн
    deadline = opp.get("deadline") or opp.get("deadline_raw", "")
    if deadline:
        # Проверяем близость дедлайна
        try:
            dl_date = date.fromisoformat(deadline)
            days_left = (dl_date - date.today()).days
            if days_left <= 7:
                lines.append(f"⏰ Дедлайн: {deadline} — <b>через {days_left} дн!</b>")
            elif days_left <= 14:
                lines.append(f"📅 Дедлайн: {deadline} (через {days_left} дн)")
            else:
                lines.append(f"📅 Дедлайн: {deadline}")
        except ValueError:
            lines.append(f"📅 Дедлайн: {deadline}")
    else:
        lines.append("📅 Дедлайн: уточняйте на сайте")

    # Открыт международным?
    intl = opp.get("open_to_international")
    if intl is True:
        lines.append("🌍 Международный")
    elif intl is False:
        lines.append("🇺🇸 Только резиденты")

    # Краткое описание на русском
    summary = opp.get("summary_ru", "")
    if summary:
        lines.append(f"\n<i>{summary}</i>")

    return "\n".join(lines)


def build_digest(opportunities: list[dict], digest_type: str = "new") -> list[str]:
    """
    Разбивает список возможностей на сообщения (Telegram лимит ~4096 символов).
    Возвращает список строк — каждая одно сообщение.
    """
    if not opportunities:
        return []

    now_str = datetime.now().strftime("%d.%m.%Y")

    if digest_type == "new":
        header = f"🎨 <b>Новые гранты для художников</b> — {now_str}\n"
    elif digest_type == "expiring":
        header = f"⏰ <b>Истекают дедлайны</b> — {now_str}\n"
    else:
        header = f"📋 <b>Гранты для художников</b> — {now_str}\n"

    messages = []
    current = header
    separator = "\n\n" + "─" * 30 + "\n\n"

    for i, opp in enumerate(opportunities):
        block = format_opportunity(opp, i + 1)
        candidate = current + separator + block if current != header else current + "\n" + block

        if len(candidate) > 3800:
            # Текущее сообщение полное — сохраняем, начинаем новое
            messages.append(current)
            current = block
        else:
            current = candidate

    if current:
        messages.append(current)

    # Футер к последнему сообщению
    if messages:
        total = len(opportunities)
        messages[-1] += f"\n\n<i>Всего: {total} возможностей</i>"

    return messages


def send_digest(digest_type: str = "new", days_window: int = 14) -> int:
    """
    Основная функция доставки.
    digest_type: 'new' — новые (не отправленные), 'expiring' — с близким дедлайном.
    Возвращает количество отправленных грантов.
    """
    conn = get_conn()

    if digest_type == "new":
        # Все не отправленные, quality != reject
        rows = conn.execute("""
            SELECT * FROM opportunities
            WHERE sent_at IS NULL
              AND opportunity_quality != 'reject'
              AND is_visual_art_relevant = 1
            ORDER BY
              CASE opportunity_quality
                WHEN 'high' THEN 1
                WHEN 'medium' THEN 2
                WHEN 'low' THEN 3
              END,
              first_seen_at DESC
            LIMIT 30
        """).fetchall()

    elif digest_type == "expiring":
        # Дедлайн в ближайшие N дней, ещё не отправлялись
        cutoff = (date.today() + timedelta(days=days_window)).isoformat()
        today = date.today().isoformat()
        rows = conn.execute("""
            SELECT * FROM opportunities
            WHERE deadline IS NOT NULL
              AND deadline >= ?
              AND deadline <= ?
              AND opportunity_quality IN ('high', 'medium')
              AND is_visual_art_relevant = 1
            ORDER BY deadline ASC
            LIMIT 20
        """, (today, cutoff)).fetchall()

    else:
        conn.close()
        return 0

    if not rows:
        print(f"[delivery] No opportunities for digest type '{digest_type}'")
        conn.close()
        return 0

    opps = [dict(row) for row in rows]
    messages = build_digest(opps, digest_type)

    sent_count = 0
    for msg_text in messages:
        msg_id = send_message(msg_text)
        if msg_id is not None or not _bot_token():
            sent_count += len(opps)  # условно все в этом сообщении

    # Помечаем как отправленные
    if messages:
        now = datetime.utcnow().isoformat()
        opp_ids = [o["id"] for o in opps]
        placeholders = ",".join("?" * len(opp_ids))
        conn.execute(
            f"UPDATE opportunities SET sent_at = ? WHERE id IN ({placeholders})",
            [now] + opp_ids,
        )
        # Логируем в telegram_deliveries
        for opp in opps:
            conn.execute("""
                INSERT INTO telegram_deliveries (opportunity_id, digest_type)
                VALUES (?, ?)
            """, (opp["id"], digest_type))
        conn.commit()

    conn.close()
    print(f"[delivery] Sent {digest_type} digest: {len(opps)} opportunities, {len(messages)} messages")
    return len(opps)


if __name__ == "__main__":
    # Тест форматтера без отправки (нет токена — печатает в stdout)
    test_opp = {
        "id": 1,
        "title": "Individual Awards 2025",
        "organization": "Sustainable Arts Foundation",
        "amount": "$5,000",
        "deadline": (date.today() + timedelta(days=10)).isoformat(),
        "deadline_raw": "Rolling deadline",
        "open_to_international": False,
        "opportunity_quality": "high",
        "url": "https://www.sustainableartsfoundation.org/awards",
        "summary_ru": "Фонд выдаёт по $5,000 двадцати художникам и писателям с детьми. Без ограничений по использованию средств.",
        "sent_at": None,
        "is_visual_art_relevant": 1,
    }

    messages = build_digest([test_opp, test_opp], digest_type="new")
    for i, m in enumerate(messages):
        print(f"--- Message {i+1} ({len(m)} chars) ---")
        print(m)
        print()
