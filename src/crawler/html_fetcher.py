"""
HTML Fetcher — httpx + trafilatura для статичных источников.
"""

import hashlib
import time
import httpx
import trafilatura
from datetime import datetime
from typing import Optional

from src.database.db import get_conn

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xhtml+xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def fetch_html(url: str, timeout: int = 15, retries: int = 3, delay: float = 2.0) -> tuple[Optional[str], Optional[str], int]:
    """
    Возвращает (raw_html, clean_text, status_code).
    clean_text — текст через trafilatura (убирает навигацию, рекламу).
    """
    for attempt in range(retries):
        try:
            with httpx.Client(headers=HEADERS, timeout=timeout, follow_redirects=True) as client:
                resp = client.get(url)
                raw_html = resp.text
                status = resp.status_code

                if status == 200:
                    clean = trafilatura.extract(
                        raw_html,
                        include_links=True,
                        include_tables=True,
                        no_fallback=False,
                    ) or ""
                    return raw_html, clean, status
                else:
                    return None, None, status

        except httpx.TimeoutException:
            if attempt < retries - 1:
                time.sleep(delay * (attempt + 1))
            else:
                return None, None, 0
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                return None, None, -1

    return None, None, -1


def crawl_source(source_id: str, url: str) -> dict:
    """
    Краулит один HTML-источник, сохраняет raw_page в БД.
    Возвращает результат для crawl_runs.
    """
    conn = get_conn()
    started_at = datetime.utcnow().isoformat()

    # Логируем старт
    run_id = conn.execute("""
        INSERT INTO crawl_runs (source_id, started_at, status)
        VALUES (?, ?, 'running')
    """, (source_id, started_at)).lastrowid
    conn.commit()

    raw_html, clean_text, status_code = fetch_html(url)

    if status_code == 200 and clean_text:
        chash = content_hash(clean_text)

        # Проверяем — менялась ли страница с прошлого раза
        existing = conn.execute("""
            SELECT id FROM raw_pages
            WHERE source_id = ? AND content_hash = ?
            ORDER BY crawled_at DESC LIMIT 1
        """, (source_id, chash)).fetchone()

        if not existing:
            page_id = conn.execute("""
                INSERT INTO raw_pages (source_id, url, content_hash, raw_text, status_code)
                VALUES (?, ?, ?, ?, ?)
            """, (source_id, url, chash, clean_text, status_code)).lastrowid
            is_new = True
        else:
            page_id = existing["id"]
            is_new = False

        # Обновляем источник
        conn.execute("""
            UPDATE sources SET last_checked_at = ? WHERE source_id = ?
        """, (datetime.utcnow().isoformat(), source_id))

        # Закрываем crawl_run
        conn.execute("""
            UPDATE crawl_runs
            SET finished_at = ?, status = 'ok', pages_fetched = 1
            WHERE id = ?
        """, (datetime.utcnow().isoformat(), run_id))
        conn.commit()
        conn.close()

        return {
            "ok": True,
            "source_id": source_id,
            "page_id": page_id,
            "is_new_content": is_new,
            "clean_text": clean_text,
            "status_code": status_code,
        }

    else:
        error_msg = f"HTTP {status_code}"
        conn.execute("""
            UPDATE crawl_runs
            SET finished_at = ?, status = 'error', error_message = ?
            WHERE id = ?
        """, (datetime.utcnow().isoformat(), error_msg, run_id))
        conn.commit()
        conn.close()

        return {
            "ok": False,
            "source_id": source_id,
            "error": error_msg,
            "status_code": status_code,
        }


if __name__ == "__main__":
    # Быстрый тест на одном источнике
    result = crawl_source(
        "sustainable_arts",
        "https://www.sustainableartsfoundation.org/awards"
    )
    print("ok:", result["ok"])
    if result["ok"]:
        print("new content:", result["is_new_content"])
        print("text preview:", result["clean_text"][:500])
    else:
        print("error:", result["error"])
