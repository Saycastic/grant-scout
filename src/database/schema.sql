-- Grant Scout Database Schema
-- SQLite

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- ─── Source Registry ──────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS sources (
    source_id       TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    url             TEXT NOT NULL,
    source_type     TEXT NOT NULL CHECK(source_type IN (
                        'aggregator', 'fund', 'government',
                        'residency', 'submission_platform', 'newsletter'
                    )),
    region          TEXT DEFAULT 'international',
    discipline_focus TEXT DEFAULT 'visual art',
    crawl_frequency TEXT DEFAULT 'weekly' CHECK(crawl_frequency IN (
                        'daily', 'weekly', 'monthly'
                    )),
    parser_type     TEXT NOT NULL CHECK(parser_type IN (
                        'html', 'rss', 'api', 'pdf', 'dynamic_js', 'listing'
                    )),
    trust_level     INTEGER DEFAULT 3 CHECK(trust_level BETWEEN 1 AND 5),
    requires_manual_review INTEGER DEFAULT 0,
    last_checked_at TEXT,
    status          TEXT DEFAULT 'active' CHECK(status IN ('active', 'paused', 'broken')),
    notes           TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);

-- ─── Raw crawl output ─────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS raw_pages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id       TEXT NOT NULL REFERENCES sources(source_id),
    url             TEXT NOT NULL,
    content_hash    TEXT NOT NULL,
    raw_text        TEXT,
    crawled_at      TEXT DEFAULT (datetime('now')),
    status_code     INTEGER,
    error           TEXT,
    extracted_at        TEXT,
    extraction_status   TEXT DEFAULT 'pending',
    extraction_error    TEXT
);

CREATE INDEX IF NOT EXISTS idx_raw_pages_source ON raw_pages(source_id);
CREATE INDEX IF NOT EXISTS idx_raw_pages_hash ON raw_pages(content_hash);

-- ─── Normalized opportunities ─────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS opportunities (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_key               TEXT UNIQUE NOT NULL,
    content_hash                TEXT,
    title                       TEXT NOT NULL,
    organization                TEXT,
    grant_type                  TEXT,
    discipline                  TEXT,           -- JSON array
    is_visual_art_relevant      INTEGER DEFAULT 1,
    is_contemporary_art_relevant INTEGER DEFAULT 1,
    applicant_type              TEXT,           -- JSON array
    eligible_residency          TEXT,           -- JSON array
    eligible_nationality        TEXT,           -- JSON array
    amount                      TEXT,
    currency                    TEXT,
    deadline                    TEXT,           -- ISO date
    deadline_raw                TEXT,
    application_fee             TEXT,
    is_paid_opportunity         INTEGER DEFAULT 0,
    requires_fiscal_sponsor     INTEGER DEFAULT 0,
    open_to_international       INTEGER,
    url                         TEXT,
    source_url                  TEXT,
    summary                     TEXT,
    why_relevant                TEXT,
    opportunity_quality         TEXT CHECK(opportunity_quality IN ('high', 'medium', 'low', 'reject')),
    confidence                  REAL DEFAULT 0.0,
    first_seen_at               TEXT DEFAULT (datetime('now')),
    last_updated_at             TEXT DEFAULT (datetime('now')),
    sent_at                     TEXT            -- когда отправили в Telegram
);

CREATE INDEX IF NOT EXISTS idx_opp_deadline ON opportunities(deadline);
CREATE INDEX IF NOT EXISTS idx_opp_quality ON opportunities(opportunity_quality);
CREATE INDEX IF NOT EXISTS idx_opp_sent ON opportunities(sent_at);

-- ─── Link: opportunity ↔ sources ──────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS opportunity_sources (
    opportunity_id  INTEGER REFERENCES opportunities(id),
    source_id       TEXT REFERENCES sources(source_id),
    raw_page_id     INTEGER REFERENCES raw_pages(id),
    PRIMARY KEY (opportunity_id, source_id)
);

-- ─── Crawl run log ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS crawl_runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id       TEXT REFERENCES sources(source_id),
    started_at      TEXT DEFAULT (datetime('now')),
    finished_at     TEXT,
    status          TEXT CHECK(status IN ('running', 'ok', 'error', 'partial')),
    pages_fetched   INTEGER DEFAULT 0,
    opps_found      INTEGER DEFAULT 0,
    opps_new        INTEGER DEFAULT 0,
    error_message   TEXT
);

-- ─── Telegram delivery log ────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS telegram_deliveries (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    opportunity_id  INTEGER REFERENCES opportunities(id),
    delivered_at    TEXT DEFAULT (datetime('now')),
    message_id      TEXT,
    digest_type     TEXT CHECK(digest_type IN ('new', 'expiring', 'alert'))
);
