"""
Extractor Pipeline — берёт new raw_pages из БД, прогоняет через LLM, сохраняет в opportunities.
Запуск: python -m src.extractor.pipeline [--page-id N] [--source source_id]
"""

import argparse
import json
from datetime import datetime

from src.database.db import get_conn
from src.extractor.llm_normalizer import call_llm, make_canonical_key


def process_page(page_id: int, source_url: str, clean_text: str) -> dict:
    """
    Прогоняет одну страницу через LLM и сохраняет результаты в БД.
    Возвращает статистику: {"processed": N, "new": N, "skipped": N, "errors": N}
    """
    conn = get_conn()
    stats = {"processed": 0, "new": 0, "skipped": 0, "errors": 0}

    try:
        grants = call_llm(clean_text, source_url)
    except Exception as e:
        print(f"[extractor] LLM error for page {page_id}: {e}")
        stats["errors"] += 1
        return stats

    print(f"[extractor] Page {page_id}: LLM returned {len(grants)} grants")

    for g in grants:
        stats["processed"] += 1
        try:
            # Алиасы — LLM иногда возвращает нестандартные поля
            org = g.get("organization") or g.get("funder") or g.get("org") or ""
            title = g.get("title") or g.get("name") or g.get("grant_name") or ""
            deadline = g.get("deadline") or g.get("deadline_date") or ""
            url = g.get("url") or g.get("website") or g.get("application_url") or source_url

            if not title:
                stats["skipped"] += 1
                continue

            # Reject-фильтр от LLM
            if g.get("opportunity_quality") == "reject":
                print(f"[extractor] REJECT (LLM): {title}")
                stats["skipped"] += 1
                continue

            # Постфильтр: отсеиваем строго-нехудожественные дисциплины
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
            combined_text = f"{title} {g.get('summary', '')} {g.get('why_relevant', '')}".lower()
            if any(kw in combined_text for kw in DISCIPLINE_REJECT_KEYWORDS):
                print(f"[extractor] REJECT (keyword filter): {title}")
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

            # Вставляем новую возможность
            opp_id = conn.execute("""
                INSERT INTO opportunities (
                    canonical_key, title, organization, grant_type,
                    discipline, is_visual_art_relevant, is_contemporary_art_relevant,
                    applicant_type, eligible_residency, eligible_nationality,
                    amount, currency, deadline, deadline_raw,
                    application_fee, is_paid_opportunity, requires_fiscal_sponsor,
                    open_to_international, url, source_url,
                    summary_ru, why_relevant_ru,
                    opportunity_quality, confidence
                ) VALUES (
                    ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
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
                g.get("deadline"),
                g.get("deadline_raw", ""),
                g.get("application_fee", ""),
                int(g.get("is_paid_opportunity", False)),
                int(g.get("requires_fiscal_sponsor", False)),
                g.get("open_to_international_applicants"),
                url,
                source_url,
                g.get("summary") or g.get("summary_ru", ""),
                g.get("why_relevant") or g.get("why_relevant_ru", ""),
                g.get("opportunity_quality", "medium"),
                float(g.get("confidence", 0.5)),
            )).lastrowid
            conn.commit()

            # Линкуем к источнику
            conn.execute("""
                INSERT OR IGNORE INTO opportunity_sources (opportunity_id, raw_page_id)
                VALUES (?, ?)
            """, (opp_id, page_id))
            conn.commit()

            stats["new"] += 1
            print(f"[extractor] NEW [{g.get('opportunity_quality','?')}]: {title[:60]}")

        except Exception as e:
            print(f"[extractor] Error saving grant '{g.get('title', '?')}': {e}")
            stats["errors"] += 1

    conn.close()
    return stats


def run_extractor(page_id: int = None, source_id: str = None):
    """
    Извлекает необработанные страницы из raw_pages и прогоняет через LLM.
    """
    conn = get_conn()

    if page_id:
        query = "SELECT id, source_id, url, raw_text FROM raw_pages WHERE id = ?"
        params = [page_id]
    elif source_id:
        query = """
            SELECT rp.id, rp.source_id, rp.url, rp.raw_text
            FROM raw_pages rp
            WHERE rp.source_id = ?
            ORDER BY rp.crawled_at DESC LIMIT 10
        """
        params = [source_id]
    else:
        # Все страницы — дедупликация идёт внутри process_page по canonical_key
        query = """
            SELECT id, source_id, url, raw_text
            FROM raw_pages
            WHERE status_code = 200 AND raw_text IS NOT NULL
            ORDER BY crawled_at DESC
            LIMIT 50
        """
        params = []

    pages = conn.execute(query, params).fetchall()
    conn.close()

    if not pages:
        print("[extractor] No pages to process.")
        return

    print(f"[extractor] Processing {len(pages)} pages...")
    total = {"processed": 0, "new": 0, "skipped": 0, "errors": 0}

    for page in pages:
        if not page["raw_text"]:
            continue

        source = conn = get_conn()
        src = conn.execute("SELECT url FROM sources WHERE source_id = ?",
                           (page["source_id"],)).fetchone()
        conn.close()
        source_url = src["url"] if src else page["url"]

        stats = process_page(page["id"], source_url, page["raw_text"])
        for k in total:
            total[k] += stats[k]

    print(f"[extractor] Done: {total['new']} new, {total['skipped']} skipped, {total['errors']} errors")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--page-id", type=int, default=None)
    parser.add_argument("--source", default=None)
    args = parser.parse_args()
    run_extractor(page_id=args.page_id, source_id=args.source)
