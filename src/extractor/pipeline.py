"""
Extractor Pipeline — берёт необработанные raw_pages из БД, прогоняет через LLM, сохраняет в opportunities.
Запуск: python -m src.extractor.pipeline [--page-id N] [--source source_id]
"""

import argparse
import json
import re
from datetime import datetime

from src.database.db import get_conn
from src.extractor.llm_normalizer import call_llm, make_canonical_key
from src.extractor.cost_guard import check_limits, log_call, reset_run_counter


DISCIPLINE_REJECT_KEYWORDS = [
    "photography only", "photographers only", "photo contest",
    "graphic design", "industrial design", "product design",
    "film festival", "screenplay", "documentary film",
    "music composition", "composers only", "songwriting",
    "literature", "poetry contest", "short story",
    "architecture competition", "architectural design",
    "fashion design", "textile design",
    "illustration contest", "book illustration",
]


def validate_grant(g: dict, source_url: str) -> dict:
    """Валидирует и нормализует поля гранта от LLM."""
    # Алиасы полей
    g["organization"] = g.get("organization") or g.get("funder") or g.get("org") or ""
    g["title"] = g.get("title") or g.get("name") or g.get("grant_name") or ""
    g["deadline"] = g.get("deadline") or g.get("deadline_date") or None
    g["url"] = g.get("url") or g.get("website") or g.get("application_url") or source_url
    g["summary"] = g.get("summary") or g.get("summary_ru") or ""
    g["why_relevant"] = g.get("why_relevant") or g.get("why_relevant_ru") or ""

    # deadline должен быть YYYY-MM-DD или None
    if g["deadline"]:
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(g["deadline"])):
            g["deadline_raw"] = g["deadline"]
            g["deadline"] = None
        else:
            g.setdefault("deadline_raw", g["deadline"])
    else:
        g["deadline"] = None

    # confidence: 0.0–1.0
    try:
        g["confidence"] = max(0.0, min(1.0, float(g.get("confidence", 0.5))))
    except (TypeError, ValueError):
        g["confidence"] = 0.5

    # opportunity_quality
    if g.get("opportunity_quality") not in ("high", "medium", "low", "reject"):
        g["opportunity_quality"] = "medium"

    # списки
    for field in ("discipline", "applicant_type", "eligible_residency", "eligible_nationality"):
        if not isinstance(g.get(field), list):
            g[field] = []

    # URL валидация
    if not str(g["url"]).startswith(("http://", "https://")):
        g["url"] = source_url

    # deadline_type
    valid_types = ("fixed", "rolling", "recurring", "tba", "closed", "unknown")
    if g.get("deadline_type") not in valid_types:
        g["deadline_type"] = "fixed" if g["deadline"] else "unknown"

    return g


def process_page(page_id: int, source_id: str, source_url: str, clean_text: str) -> dict:
    """
    Прогоняет одну страницу через LLM и сохраняет результаты в БД.
    Возвращает статистику: {"processed": N, "new": N, "skipped": N, "errors": N}
    """
    conn = get_conn()
    stats = {"processed": 0, "new": 0, "skipped": 0, "errors": 0}

    # Cost guard
    ok, reason = check_limits()
    if not ok:
        print(f"[extractor] COST GUARD: skipping page {page_id} — {reason}")
        stats["skipped"] += 1
        return stats

    try:
        grants = call_llm(clean_text, source_url)
    except Exception as e:
        print(f"[extractor] LLM error for page {page_id}: {e}")
        conn.execute(
            "UPDATE raw_pages SET extracted_at=?, extraction_status='error', extraction_error=? WHERE id=?",
            (datetime.utcnow().isoformat(), str(e), page_id)
        )
        conn.commit()
        conn.close()
        stats["errors"] += 1
        return stats

    print(f"[extractor] Page {page_id}: LLM returned {len(grants)} grants")
    log_call(source_id, page_id, len(clean_text), len(grants))

    for g in grants:
        stats["processed"] += 1
        try:
            g = validate_grant(g, source_url)

            title = g["title"]
            org = g["organization"]
            deadline = g["deadline"]
            url = g["url"]

            if not title:
                stats["skipped"] += 1
                continue

            # Reject-фильтр от LLM
            if g.get("opportunity_quality") == "reject":
                print(f"[extractor] REJECT (LLM): {title}")
                stats["skipped"] += 1
                continue

            # Постфильтр по дате — если дедлайн прошёл, выбрасываем
            if deadline:
                today = datetime.utcnow().date().isoformat()
                if deadline < today:
                    print(f"[extractor] REJECT (expired {deadline}): {title}")
                    stats["skipped"] += 1
                    continue

            # Постфильтр по ключевым словам дисциплины
            combined_text = f"{title} {g.get('summary', '')} {g.get('why_relevant', '')}".lower()
            if any(kw in combined_text for kw in DISCIPLINE_REJECT_KEYWORDS):
                print(f"[extractor] REJECT (keyword): {title}")
                stats["skipped"] += 1
                continue

            canonical_key = make_canonical_key(org, title, deadline or "", url)

            existing = conn.execute(
                "SELECT id FROM opportunities WHERE canonical_key = ?",
                (canonical_key,)
            ).fetchone()

            if existing:
                stats["skipped"] += 1
                continue

            opp_id = conn.execute("""
                INSERT INTO opportunities (
                    canonical_key, title, organization, grant_type,
                    discipline, is_visual_art_relevant, is_contemporary_art_relevant,
                    applicant_type, eligible_residency, eligible_nationality,
                    amount, currency, deadline, deadline_raw,
                    application_fee, is_paid_opportunity, requires_fiscal_sponsor,
                    open_to_international, url, source_url,
                    summary, why_relevant,
                    opportunity_quality, confidence,
                    deadline_type, deadline_notes
                ) VALUES (
                    ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?,
                    ?, ?,
                    ?, ?
                )
            """, (
                canonical_key,
                title,
                org,
                g.get("grant_type", ""),
                json.dumps(g.get("discipline", []), ensure_ascii=False),
                int(g.get("is_visual_art_relevant", True)),
                int(g.get("is_contemporary_art_relevant", True)),
                json.dumps(g.get("applicant_type", []), ensure_ascii=False),
                json.dumps(g.get("eligible_residency", []), ensure_ascii=False),
                json.dumps(g.get("eligible_nationality", []), ensure_ascii=False),
                g.get("amount", ""),
                g.get("currency", ""),
                deadline,
                g.get("deadline_raw", ""),
                g.get("application_fee", ""),
                int(g.get("is_paid_opportunity", False)),
                int(g.get("requires_fiscal_sponsor", False)),
                g.get("open_to_international_applicants"),
                url,
                source_url,
                g.get("summary", ""),
                g.get("why_relevant", ""),
                g.get("opportunity_quality", "medium"),
                g.get("confidence", 0.5),
                g.get("deadline_type", "unknown"),
                g.get("deadline_notes", ""),
            )).lastrowid
            conn.commit()

            # Линкуем к источнику с source_id
            conn.execute("""
                INSERT OR IGNORE INTO opportunity_sources (opportunity_id, source_id, raw_page_id)
                VALUES (?, ?, ?)
            """, (opp_id, source_id, page_id))
            conn.commit()

            stats["new"] += 1
            print(f"[extractor] NEW [{g.get('opportunity_quality','?')}]: {title[:60]}")

        except Exception as e:
            print(f"[extractor] Error saving grant '{g.get('title', '?')}': {e}")
            stats["errors"] += 1

    # Помечаем страницу как обработанную
    conn.execute(
        "UPDATE raw_pages SET extracted_at=?, extraction_status='ok' WHERE id=?",
        (datetime.utcnow().isoformat(), page_id)
    )
    conn.commit()
    conn.close()
    return stats


def run_extractor(page_id: int = None, source_id: str = None):
    """
    Извлекает ТОЛЬКО необработанные страницы (extracted_at IS NULL) из raw_pages.
    """
    conn = get_conn()

    reset_run_counter()

    if page_id:
        query = "SELECT id, source_id, url, raw_text FROM raw_pages WHERE id = ?"
        params = [page_id]
    elif source_id:
        query = """
            SELECT id, source_id, url, raw_text
            FROM raw_pages
            WHERE source_id = ?
              AND status_code = 200
              AND raw_text IS NOT NULL
              AND extracted_at IS NULL
            ORDER BY crawled_at DESC LIMIT 20
        """
        params = [source_id]
    else:
        # Только необработанные — ключевой фикс
        query = """
            SELECT id, source_id, url, raw_text
            FROM raw_pages
            WHERE status_code = 200
              AND raw_text IS NOT NULL
              AND extracted_at IS NULL
            ORDER BY crawled_at DESC
            LIMIT 50
        """
        params = []

    pages = conn.execute(query, params).fetchall()
    conn.close()

    if not pages:
        print("[extractor] No new pages to process.")
        return

    print(f"[extractor] Processing {len(pages)} new pages...")
    total = {"processed": 0, "new": 0, "skipped": 0, "errors": 0}

    for page in pages:
        if not page["raw_text"]:
            continue

        conn2 = get_conn()
        src = conn2.execute("SELECT url FROM sources WHERE source_id = ?",
                            (page["source_id"],)).fetchone()
        conn2.close()
        source_url = src["url"] if src else page["url"]

        stats = process_page(page["id"], page["source_id"], source_url, page["raw_text"])
        for k in total:
            total[k] += stats[k]

    print(f"[extractor] Done: {total['new']} new, {total['skipped']} skipped, {total['errors']} errors")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--page-id", type=int, default=None)
    parser.add_argument("--source", default=None)
    args = parser.parse_args()
    run_extractor(page_id=args.page_id, source_id=args.source)
