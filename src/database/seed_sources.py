"""
Source Registry — начальный список источников.
Запусти: python -m src.database.seed_sources
"""

from src.database.db import get_conn, init_db

SOURCES = [
    # ── Агрегаторы высокой плотности ──────────────────────────────────────────
    {
        "source_id": "nyfa_opportunities",
        "name": "NYFA Opportunities — Visual Arts Grants",
        "url": "https://www.nyfa.org/opportunities/?discipline=Visual+Arts&type=Grant",
        "source_type": "aggregator",
        "region": "usa",
        "crawl_frequency": "weekly",
        "parser_type": "dynamic_js",
        "trust_level": 5,
        "notes": "Подтверждено: JS-рендеринг, Playwright. 48K символов контента.",
    },
    {
        "source_id": "artconnect",
        "parser_type": "listing",
        "name": "ArtConnect Grants & Stipends",
        "url": "https://www.artconnect.com/opportunities/grant-or-stipend",
        "source_type": "aggregator",
        "region": "international",
        "crawl_frequency": "daily",
        "parser_type": "html",
        "trust_level": 5,
        "notes": "Международные гранты, стипендии, open calls. Актуальный URL с фильтром.",
    },
    {
        "source_id": "on_the_move",
        "name": "On the Move — Funding Guides",
        "url": "https://on-the-move.org/resources/funding",
        "source_type": "aggregator",
        "region": "international",
        "crawl_frequency": "weekly",
        "parser_type": "html",
        "trust_level": 5,
        "notes": "2000+ grants, scholarships, residencies. Mobility и international funding.",
    },
    {
        "source_id": "culture_moves_europe",
        "name": "Culture Moves Europe",
        "url": "https://culture.ec.europa.eu/culture-moves-europe",
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
        "parser_type": "listing",
        "trust_level": 4,
        "notes": "Листинг-агрегатор. Парсим каждую страницу /ops/ отдельно через listing_fetcher.",
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
        "notes": "Marketplace. JS-рендеринг через Playwright.",
    },
    {
        "source_id": "beam_arts",
        "name": "Beam Arts — Artist Funding Directory",
        "url": "https://www.beamarts.gr/artist-funding-directory",
        "source_type": "aggregator",
        "region": "international",
        "crawl_frequency": "weekly",
        "parser_type": "html",
        "trust_level": 4,
        "notes": "Каталог grants/funding worldwide для artists. Обновлён февраль 2026.",
    },
    {
        "source_id": "fractured_atlas",
        "name": "Fractured Atlas — Artist Opportunity Database",
        "url": "https://fracturedatlas.notion.site/Artist-Opportunity-Database",
        "source_type": "aggregator",
        "region": "international",
        "crawl_frequency": "weekly",
        "parser_type": "html",
        "trust_level": 4,
        "notes": "Notion-база: grants, funders, awards, fellowships, open calls, residencies worldwide.",
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
        "source_id": "creative_capital",
        "name": "Creative Capital Foundation",
        "url": "https://creative-capital.org/awards/",
        "source_type": "fund",
        "region": "usa",
        "crawl_frequency": "monthly",
        "parser_type": "dynamic_js",
        "trust_level": 5,
        "notes": "JS-рендеринг, Playwright. Страница awards с актуальными грантами.",
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
        "notes": "$5,000 x 20 художников. Для artists с детьми.",
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
        "notes": "HTML + JSON-LD. Дедлайны по городам (LA, Chicago, NYC, SF).",
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
        "notes": "Residency fellowships, включая visual arts.",
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
        "notes": "Grants для visual artists.",
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
        "notes": "Playwright нужен.",
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
        "notes": "USA Fellows program.",
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
        "notes": "$25,000 grants to women visual artists 45+.",
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
        "notes": "Гранты организациям, поддерживающим contemporary visual art.",
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
        "notes": "Playwright нужен.",
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
        "notes": "Стипендии, резиденции, проектные гранты.",
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
        "notes": "Grants for international projects.",
    },
]


def seed():
    init_db()
    conn = get_conn()
    upserted = 0
    with conn:
        for s in SOURCES:
            try:
                conn.execute("""
                    INSERT INTO sources
                    (source_id, name, url, source_type, region, discipline_focus,
                     crawl_frequency, parser_type, trust_level, requires_manual_review, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(source_id) DO UPDATE SET
                        name = excluded.name,
                        url = excluded.url,
                        source_type = excluded.source_type,
                        region = excluded.region,
                        discipline_focus = excluded.discipline_focus,
                        crawl_frequency = excluded.crawl_frequency,
                        parser_type = excluded.parser_type,
                        trust_level = excluded.trust_level,
                        requires_manual_review = excluded.requires_manual_review,
                        notes = excluded.notes
                """, (
                    s["source_id"], s["name"], s["url"], s["source_type"],
                    s.get("region", "international"), s.get("discipline_focus", "visual art"),
                    s.get("crawl_frequency", "weekly"), s["parser_type"],
                    s.get("trust_level", 3), s.get("requires_manual_review", 0),
                    s.get("notes", ""),
                ))
                upserted += 1
            except Exception as e:
                print(f"Error upserting {s['source_id']}: {e}")

    print(f"Seeded: {upserted} sources upserted.")
    conn.close()


if __name__ == "__main__":
    seed()
