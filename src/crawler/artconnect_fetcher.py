"""
ArtConnect API fetcher — краулит гранты напрямую через внутренний API artconnect.com.
Авторизация через сохранённые куки (обновляются автоматически при протухании).
"""

import os
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx

from src.database.db import get_conn

# ─── Пути ────────────────────────────────────────────────────────────────────
_BASE = Path(__file__).parent.parent.parent
COOKIES_FILE = _BASE / "data" / "artconnect_cookies.json"
ENV_FILE = _BASE / ".env"

# Load .env
if ENV_FILE.exists():
    for _line in ENV_FILE.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

API_BASE = "https://api.artconnect.com/v1"
SITE_BASE = "https://www.artconnect.com"


# ─── Авторизация ─────────────────────────────────────────────────────────────

def _load_cookies() -> Optional[dict]:
    if COOKIES_FILE.exists():
        raw = json.loads(COOKIES_FILE.read_text())
        return {c["name"]: c["value"] for c in raw}
    return None


async def _playwright_login() -> dict:
    """Логинится через Playwright, сохраняет и возвращает куки."""
    from playwright.async_api import async_playwright

    email = os.environ.get("ARTCONNECT_EMAIL", "")
    password = os.environ.get("ARTCONNECT_PASSWORD", "")
    if not email or not password:
        raise RuntimeError("ARTCONNECT_EMAIL / ARTCONNECT_PASSWORD not set in .env")

    print("[artconnect] Logging in via Playwright...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context()
        page = await ctx.new_page()

        await page.goto(f"{SITE_BASE}/login", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)

        # Dismiss cookie banner
        try:
            accept = await page.query_selector('[data-cky-tag="accept-button"]')
            if accept:
                await accept.click()
                await page.wait_for_timeout(500)
        except Exception:
            pass

        await page.fill('input[name="email"]', email)
        await page.fill('input[name="password"]', password)
        await page.wait_for_timeout(300)
        await page.click('button:has-text("Sign in")')
        await page.wait_for_timeout(5000)

        if "/login" in page.url:
            raise RuntimeError("ArtConnect login failed — check credentials")

        cookies_raw = await ctx.cookies()
        COOKIES_FILE.parent.mkdir(exist_ok=True)
        COOKIES_FILE.write_text(json.dumps(cookies_raw, indent=2))
        print(f"[artconnect] Logged in, saved {len(cookies_raw)} cookies")

        await browser.close()
        return {c["name"]: c["value"] for c in cookies_raw}


def _get_or_login_cookies() -> dict:
    """Возвращает куки — из файла или логинится заново."""
    cookies = _load_cookies()
    if cookies:
        return cookies
    return asyncio.run(_playwright_login())


# ─── API запросы ─────────────────────────────────────────────────────────────

def _api_get(path: str, params: dict, cookies: dict) -> Optional[dict]:
    try:
        r = httpx.get(
            f"{API_BASE}{path}",
            params=params,
            cookies=cookies,
            headers={"User-Agent": "Mozilla/5.0", "Referer": SITE_BASE},
            timeout=15,
        )
        if r.status_code == 401:
            return None  # нужен перелогин
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[artconnect] API error {path}: {e}")
        return None


# ─── Нормализация данных ─────────────────────────────────────────────────────

def _item_to_text(item: dict) -> str:
    """Преобразует JSON объявления в plain text для экстрактора."""
    lines = []

    title = item.get("title", "")
    lines.append(f"Title: {title}")

    profile = item.get("profile", {})
    org = profile.get("organizationName") or f"{profile.get('firstName','')} {profile.get('lastName','')}".strip()
    lines.append(f"Organization: {org}")

    country = item.get("country", "") or profile.get("country", "")
    city = item.get("city", "") or profile.get("city", "")
    if city or country:
        lines.append(f"Location: {city}, {country}".strip(", "))

    deadline = item.get("deadline")
    if deadline:
        lines.append(f"Deadline: {deadline[:10]}")

    fields = item.get("artisticFields", []) or []
    if fields:
        lines.append(f"Artistic fields: {', '.join(fields)}")

    rewards = item.get("rewards", []) or []
    for r in rewards:
        if isinstance(r, dict):
            amount = r.get("amount") or r.get("description", "")
            if amount:
                lines.append(f"Reward: {amount}")

    fees = item.get("applicationFees") or item.get("fee", "")
    lines.append(f"Application fee: {'No' if not fees or fees == 'FREE' else fees}")

    # Описание — может быть массивом блоков
    desc = item.get("description", []) or []
    desc_text = ""
    if isinstance(desc, list):
        for block in desc:
            if isinstance(block, dict):
                desc_text += block.get("content", "") + "\n"
    elif isinstance(desc, str):
        desc_text = desc
    if desc_text.strip():
        lines.append(f"\nDescription:\n{desc_text.strip()[:3000]}")

    restrictions = item.get("restrictions", {}) or {}
    eligibility = []
    for k, v in restrictions.items():
        if v:
            eligibility.append(f"{k}: {v}")
    if eligibility:
        lines.append(f"Eligibility: {'; '.join(eligibility)}")

    url = f"{SITE_BASE}/opportunity/{item['id']}"
    lines.append(f"URL: {url}")

    return "\n".join(lines)


# ─── Сохранение в raw_pages ───────────────────────────────────────────────────

def _save_raw_page(source_id: str, url: str, text: str) -> dict:
    import hashlib
    if not text.strip():
        return {"ok": False, "error": "empty content"}

    content_hash = hashlib.sha256(text.encode()).hexdigest()
    conn = get_conn()
    now = datetime.utcnow().isoformat()
    try:
        existing = conn.execute(
            "SELECT id, content_hash FROM raw_pages WHERE url = ?", (url,)
        ).fetchone()

        if existing:
            if existing["content_hash"] == content_hash:
                return {"ok": True, "is_new_content": False}
            conn.execute(
                "UPDATE raw_pages SET raw_text=?, content_hash=?, crawled_at=?, "
                "extracted_at=NULL, extraction_status='pending' WHERE id=?",
                (text, content_hash, now, existing["id"]),
            )
        else:
            conn.execute(
                "INSERT INTO raw_pages (source_id, url, raw_text, content_hash, crawled_at, extraction_status) "
                "VALUES (?, ?, ?, ?, ?, 'pending')",
                (source_id, url, text, content_hash, now),
            )
        conn.commit()
        return {"ok": True, "is_new_content": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()


# ─── Основная функция краулинга ───────────────────────────────────────────────

def crawl_artconnect() -> dict:
    """
    Краулит все гранты с ArtConnect через API.
    Возвращает {ok, source_id, total, new, errors}
    """
    source_id = "artconnect"
    cookies = _get_or_login_cookies()

    # Пробуем API — если 401, перелогиниваемся
    test = _api_get("/opportunities/", {"types": "GRANT_OR_STIPEND", "limit": 1, "page": 1}, cookies)
    if test is None:
        print("[artconnect] Session expired, re-logging in...")
        cookies = asyncio.run(_playwright_login())
        test = _api_get("/opportunities/", {"types": "GRANT_OR_STIPEND", "limit": 1, "page": 1}, cookies)
        if test is None:
            return {"ok": False, "source_id": source_id, "error": "API unavailable after re-login"}

    total_pages = test.get("pages", 1)
    print(f"[artconnect] {total_pages} pages of grants")

    all_items = []
    for page_num in range(1, total_pages + 1):
        data = _api_get("/opportunities/", {
            "types": "GRANT_OR_STIPEND",
            "sortBy": "-deadline",
            "limit": 10,
            "page": page_num,
        }, cookies)
        if data is None:
            print(f"[artconnect] Page {page_num} failed")
            continue
        items = data.get("data", [])
        all_items.extend(items)
        print(f"[artconnect] Page {page_num}/{total_pages}: {len(items)} items")

    new_count = 0
    error_count = 0
    for item in all_items:
        url = f"{SITE_BASE}/opportunity/{item['id']}"
        text = _item_to_text(item)
        result = _save_raw_page(source_id, url, text)
        if result.get("ok") and result.get("is_new_content"):
            new_count += 1
        elif not result.get("ok"):
            error_count += 1

    print(f"[artconnect] Done: {len(all_items)} total, {new_count} new, {error_count} errors")
    return {
        "ok": True,
        "source_id": source_id,
        "total": len(all_items),
        "new": new_count,
        "errors": error_count,
        "is_new_content": new_count > 0,
    }
