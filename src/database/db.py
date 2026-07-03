import sqlite3
import os
from pathlib import Path

DB_PATH = os.environ.get("GRANT_SCOUT_DB", str(Path(__file__).parent.parent.parent / "data" / "grant_scout.db"))
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_conn() -> sqlite3.Connection:
    # Автоинициализация схемы если БД не существует
    if not Path(DB_PATH).exists():
        init_db()
        from src.database.seed_sources import seed
        seed()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    schema = SCHEMA_PATH.read_text()
    with get_conn() as conn:
        conn.executescript(schema)
    print(f"DB initialised at {DB_PATH}")


if __name__ == "__main__":
    init_db()
