"""
JS Fetcher — Playwright для динамических источников.
"""

import hashlib
import time
from datetime import datetime
from typing import Optional

from src.database.db import get_conn


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def fetch_js(url: str, timeout: int = 30, wait_for: str = "domcontentloaded") -> tuple[Optional[str], int]:
    """
    Возвращает (clean_text, status_code).
    Playwright нужен только для dynamic_js источников.
    """
    try:
        from playwright.sync_api import sync_playwright
        import trafilatura

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                locale="en-US",
            )
            page = context.new_page()

            response = page.goto(url, timeout=timeout * 1000, wait_until=wait_for)
            status_code = response.status if response else 0

            if status_code in (200, 0):
                # Ждём чуть-чуть и скроллим чтобы активировать lazy-load
                page.wait_for_timeout(2000)
                page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
                page.wait_for_timeout(1500)

                html = page.content()
                clean = trafilatura.extract(
                    html,
                    include_links=True,
                    include_tables=True,
                    no_fallback=False,
                ) or ""
                browser.close()
                return clean, 200 if status_code == 0 else status_code
            else:
                browser.close()
                return None, status_code

    except ImportError:
        print("[js_fetcher] Playwright не установлен. Установи: pip install playwright && playwright install chromium")
        return None, -2
    except Exception as e:
        print(f"[js_fetcher] Error: {e}")
        return None, -1


def crawl_source_js(source_id: str, url: str) -> dict:
    """
    Краулит JS-источник, сохраняет raw_page в БД.
    """
    conn = get_conn()
    started_at = datetime.utcnow().isoformat()

    run_id = conn.execute("""
        INSERT INTO crawl_runs (source_id, started_at, status)
        VALUES (?, ?, 'running')
    """, (source_id, started_at)).lastrowid
    conn.commit()

    clean_text, status_code = fetch_js(url)

    if status_code == 200 and clean_text:
        chash = content_hash(clean_text)

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

        conn.execute("UPDATE sources SET last_checked_at = ? WHERE source_id = ?",
                     (datetime.utcnow().isoformat(), source_id))
        conn.execute("""
            UPDATE crawl_runs SET finished_at = ?, status = 'ok', pages_fetched = 1
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
            UPDATE crawl_runs SET finished_at = ?, status = 'error', error_message = ?
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
    result = crawl_source_js(
        "nyfa_opportunities",
        "https://www.nyfa.org/opportunities/?discipline=Visual+Arts&type=Grant"
    )
    print("ok:", result["ok"])
    if result["ok"]:
        print("new content:", result["is_new_content"])
        print("text preview:", result["clean_text"][:500])
    else:
        print("error:", result["error"])
