"""
Source Registry — начальный список источников.
Запусти: python -m src.database.seed_sources
"""

import json
from src.database.db import get_conn, init_db

SOURCES = [
    # ── Агрегаторы высокой плотности ──────────────────────────────────────────
    {
        "source_id": "nyfa_opportunities",
        "name": "NYFA Opportunities Board",
        "url": "https://www.nyfa.org/opportunities/?discipline=Visual+Arts&type=Grant",
        "source_type": "aggregator",
        "region": "international",
        "crawl_frequency": "daily",
        "parser_type": "dynamic_js",
        "trust_level": 5,
        "notes": "Лучший агрегатор грантов для художников в США и international. JS-рендеринг, нужен Playwright.",
    },
    {
        "source_id": "artconnect",
        "name": "ArtConnect Grants & Stipends",
        "url": "https://www.artconnect.com/opportunities?type=grant",
        "source_type": "aggregator",
        "region": "international",
        "crawl_frequency": "daily",
        "parser_type": "html",
        "trust_level": 5,
        "notes": "Международные гранты, стипендии, open calls. Фильтр по типу в URL.",
    },
    {
        "source_id": "on_the_move",
        "name": "On the Move — Funding Guides",
        "url": "https://on-the-move.org/funding",
        "source_type": "aggregator",
        "region": "international",
        "crawl_frequency": "weekly",
        "parser_type": "html",
        "trust_level": 5,
        "notes": "Mobility grants, travel funding, international cultural exchange.",
    },
    {
        "source_id": "culture_moves_europe",
        "name": "Culture Moves Europe",
        "url": "https://culture.ec.europa.eu/policies/cultural-and-creative-sectors/culture-moves-europe",
        "source_type": "government",
        "region": "europe",
        "crawl_frequency": "weekly",
        "parser_type": "html",
        "trust_level": 5,
        "notes": "Европейская mobility-схема для artists, включая visual arts.",
    },
    {
        "source_id": "transartists",
        "name": "TransArtists / DutchCulture Funding",
        "url": "https://www.transartists.org/en/opportunities",
        "source_type": "aggregator",
        "region": "international",
        "crawl_frequency": "weekly",
        "parser_type": "html",
        "trust_level": 4,
        "notes": "Резиденции и funding for residencies, международная мобильность.",
    },
    {
        "source_id": "res_artis",
        "name": "Res Artis — Open Calls & Funding",
        "url": "https://www.resartis.org/en/opportunities/",
        "source_type": "aggregator",
        "region": "international",
        "crawl_frequency": "weekly",
        "parser_type": "html",
        "trust_level": 4,
        "notes": "Residency-related funding и open calls от мировых резиденций.",
    },
    {
        "source_id": "artdeadline",
        "name": "ArtDeadline.com — Grants",
        "url": "https://artdeadline.com/?type=Grant",
        "source_type": "aggregator",
        "region": "international",
        "crawl_frequency": "daily",
        "parser_type": "html",
        "trust_level": 4,
        "notes": "Парсится без Cloudflare. Базовые листинги доступны без подписки.",
    },
    {
        "source_id": "submittable_discover",
        "name": "Submittable Discover — Grants",
        "url": "https://www.submittable.com/discover/?category=grants&q=visual+art",
        "source_type": "submission_platform",
        "region": "international",
        "crawl_frequency": "daily",
        "parser_type": "dynamic_js",
        "trust_level": 4,
        "notes": "Marketplace. Скорее всего GraphQL API под капотом — нужно исследовать.",
    },
    {
        "source_id": "beam_arts",
        "name": "Beam Arts — Artist Funding Directory",
        "url": "https://beamarts.org/funding",
        "source_type": "aggregator",
        "region": "international",
        "crawl_frequency": "weekly",
        "parser_type": "html",
        "trust_level": 4,
        "notes": "Каталог организаций, которые дают funding/grants artists worldwide.",
    },
    {
        "source_id": "fractured_atlas",
        "name": "Fractured Atlas — Artist Opportunity Database",
        "url": "https://www.fracturedatlas.org/artist-resources/funding/",
        "source_type": "aggregator",
        "region": "international",
        "crawl_frequency": "weekly",
        "parser_type": "html",
        "trust_level": 4,
        "notes": "Artist grants, funders, awards, fellowships, open calls, residencies worldwide.",
    },

    # ── Прямые фонды — визуальное искусство ────────────────────────────────────
    {
        "source_id": "fca_emergency",
        "name": "Foundation for Contemporary Arts — Emergency Grants",
        "url": "https://www.foundationforcontemporaryarts.org/grants/emergency-grants/",
        "source_type": "fund",
        "region": "usa",
        "crawl_frequency": "monthly",
        "parser_type": "html",
        "trust_level": 5,
        "notes": "Срочные гранты $500-$3,000 для visual и performing artists в США. Открыты круглый год.",
    },
    {
        "source_id": "fca_application",
        "name": "Foundation for Contemporary Arts — Grants by Application",
        "url": "https://www.foundationforcontemporaryarts.org/grants/by-application/",
        "source_type": "fund",
        "region": "usa",
        "crawl_frequency": "monthly",
        "parser_type": "html",
        "trust_level": 5,
        "notes": "Гранты FCA по заявке — основная программа для художников.",
    },
    {
        "source_id": "sustainable_arts",
        "name": "Sustainable Arts Foundation",
        "url": "https://www.sustainableartsfoundation.org/awards",
        "source_type": "fund",
        "region": "usa",
        "crawl_frequency": "monthly",
        "parser_type": "html",
        "trust_level": 5,
        "notes": "Подтверждено: статичный HTML. $5,000 x 20 художников. Для artists с детьми.",
    },
    {
        "source_id": "artadia",
        "name": "Artadia Awards",
        "url": "https://artadia.org/awards/",
        "source_type": "fund",
        "region": "usa",
        "crawl_frequency": "monthly",
        "parser_type": "html",
        "trust_level": 5,
        "notes": "Подтверждено: HTML + JSON-LD. Дедлайны по городам (LA, Chicago, NYC, SF).",
    },
    {
        "source_id": "macdowell",
        "name": "MacDowell Fellowships",
        "url": "https://macdowell.org/fellowships/",
        "source_type": "residency",
        "region": "usa",
        "crawl_frequency": "monthly",
        "parser_type": "html",
        "trust_level": 4,
        "notes": "Подтверждено: HTML. Residency fellowships, включая visual arts.",
    },
    {
        "source_id": "joan_mitchell",
        "name": "Joan Mitchell Foundation — Grants",
        "url": "https://joanmitchellfoundation.org/grants/",
        "source_type": "fund",
        "region": "usa",
        "crawl_frequency": "monthly",
        "parser_type": "html",
        "trust_level": 5,
        "notes": "404 на /artist-programs/grants/ — нужно найти правильный URL.",
        "requires_manual_review": 1,
    },
    {
        "source_id": "creative_capital",
        "name": "Creative Capital",
        "url": "https://creative-capital.org/awards/",
        "source_type": "fund",
        "region": "usa",
        "crawl_frequency": "monthly",
        "parser_type": "dynamic_js",
        "trust_level": 5,
        "notes": "403 при прямом curl — нужен Playwright или User-Agent ротация.",
    },
    {
        "source_id": "pollock_krasner",
        "name": "Pollock-Krasner Foundation",
        "url": "https://pkf.org/our-grants/",
        "source_type": "fund",
        "region": "international",
        "crawl_frequency": "monthly",
        "parser_type": "dynamic_js",
        "trust_level": 5,
        "notes": "403 при прямом curl — нужен Playwright.",
    },
    {
        "source_id": "usa_artists",
        "name": "United States Artists",
        "url": "https://www.unitedstatesartists.org/",
        "source_type": "fund",
        "region": "usa",
        "crawl_frequency": "monthly",
        "parser_type": "html",
        "trust_level": 5,
        "notes": "Главная 200, /usa-fellows/ 404. Нужно найти правильный URL fellowships.",
        "requires_manual_review": 1,
    },
    {
        "source_id": "anonymous_was_a_woman",
        "name": "Anonymous Was A Woman",
        "url": "https://anonymouswasawoman.org/",
        "source_type": "fund",
        "region": "usa",
        "crawl_frequency": "monthly",
        "parser_type": "html",
        "trust_level": 4,
        "notes": "$25,000 grants to women visual artists 45+. URL /grants/ даёт 404, нужно найти правильный.",
        "requires_manual_review": 1,
    },
    {
        "source_id": "andy_warhol_fnd",
        "name": "Andy Warhol Foundation for the Visual Arts",
        "url": "https://warholfoundation.org/grant/",
        "source_type": "fund",
        "region": "international",
        "crawl_frequency": "monthly",
        "parser_type": "html",
        "trust_level": 5,
        "notes": "406 — нужен специфический Accept header или Playwright.",
    },
    {
        "source_id": "jerome_fnd",
        "name": "Jerome Foundation",
        "url": "https://jeromefdn.org/grants",
        "source_type": "fund",
        "region": "usa",
        "crawl_frequency": "monthly",
        "parser_type": "dynamic_js",
        "trust_level": 4,
        "notes": "Cloudflare на /apply. Нужен Playwright.",
    },

    # ── Европейские и международные фонды ─────────────────────────────────────
    {
        "source_id": "british_council_arts",
        "name": "British Council — Arts Funding",
        "url": "https://www.britishcouncil.org/arts/funding",
        "source_type": "government",
        "region": "uk",
        "crawl_frequency": "monthly",
        "parser_type": "html",
        "trust_level": 4,
        "notes": "Mobility и international arts grants от British Council.",
    },
    {
        "source_id": "goethe_fnd",
        "name": "Goethe-Institut — Grants & Residencies",
        "url": "https://www.goethe.de/en/kul/the/sti.html",
        "source_type": "government",
        "region": "international",
        "crawl_frequency": "monthly",
        "parser_type": "html",
        "trust_level": 4,
        "notes": "Немецкий культурный институт. Стипендии, резиденции, проектные гранты.",
    },
    {
        "source_id": "pro_helvetia",
        "name": "Pro Helvetia — Swiss Arts Council",
        "url": "https://prohelvetia.ch/en/grants/",
        "source_type": "government",
        "region": "europe",
        "crawl_frequency": "monthly",
        "parser_type": "html",
        "trust_level": 4,
        "notes": "Швейцарский совет по искусству. Grants for international projects.",
    },
]


def seed():
    init_db()
    conn = get_conn()
    inserted = 0
    skipped = 0
    with conn:
        for s in SOURCES:
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO sources
                    (source_id, name, url, source_type, region, discipline_focus,
                     crawl_frequency, parser_type, trust_level, requires_manual_review, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    s["source_id"], s["name"], s["url"], s["source_type"],
                    s.get("region", "international"), s.get("discipline_focus", "visual art"),
                    s.get("crawl_frequency", "weekly"), s["parser_type"],
                    s.get("trust_level", 3), s.get("requires_manual_review", 0),
                    s.get("notes", ""),
                ))
                if conn.execute("SELECT changes()").fetchone()[0]:
                    inserted += 1
                else:
                    skipped += 1
            except Exception as e:
                print(f"Error inserting {s['source_id']}: {e}")

    print(f"Seeded: {inserted} inserted, {skipped} already existed.")
    conn.close()


if __name__ == "__main__":
    seed()
