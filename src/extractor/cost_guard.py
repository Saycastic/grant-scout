"""
Cost Guard — ограничивает количество LLM вызовов за прогон и за день.
Логирует использование в llm_usage.
"""

import os
from datetime import datetime, date
from src.database.db import get_conn

MAX_CALLS_PER_RUN = int(os.environ.get("MAX_LLM_CALLS_PER_RUN", 60))
MAX_CALLS_PER_DAY = int(os.environ.get("MAX_LLM_CALLS_PER_DAY", 300))
MAX_CHARS_PER_CALL = int(os.environ.get("MAX_LLM_CHARS_PER_CALL", 12000))

_run_calls = 0  # счётчик текущего прогона


def reset_run_counter():
    global _run_calls
    _run_calls = 0


def check_limits() -> tuple[bool, str]:
    """
    Проверяет не превышены ли лимиты.
    Возвращает (ok, reason).
    """
    global _run_calls

    if _run_calls >= MAX_CALLS_PER_RUN:
        return False, f"run limit reached ({_run_calls}/{MAX_CALLS_PER_RUN})"

    conn = get_conn()
    today = date.today().isoformat()
    day_calls = conn.execute(
        "SELECT COUNT(*) FROM llm_usage WHERE created_at >= ?",
        (today,)
    ).fetchone()[0]
    conn.close()

    if day_calls >= MAX_CALLS_PER_DAY:
        return False, f"daily limit reached ({day_calls}/{MAX_CALLS_PER_DAY})"

    return True, "ok"


def log_call(source_id: str, raw_page_id: int, prompt_chars: int,
             opportunities_extracted: int, provider: str = "", model: str = ""):
    """Логирует один LLM вызов."""
    global _run_calls
    _run_calls += 1

    conn = get_conn()
    conn.execute("""
        INSERT INTO llm_usage
        (provider, model, prompt_chars, source_id, raw_page_id, opportunities_extracted, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (provider, model, prompt_chars, source_id, raw_page_id,
          opportunities_extracted, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()


def get_today_stats() -> dict:
    """Возвращает статистику использования LLM за сегодня."""
    conn = get_conn()
    today = date.today().isoformat()
    row = conn.execute("""
        SELECT
            COUNT(*) as calls,
            SUM(prompt_chars) as total_chars,
            SUM(opportunities_extracted) as total_extracted
        FROM llm_usage WHERE created_at >= ?
    """, (today,)).fetchone()
    conn.close()
    return {
        "calls": row[0] or 0,
        "total_chars": row[1] or 0,
        "total_extracted": row[2] or 0,
        "run_calls": _run_calls,
    }
