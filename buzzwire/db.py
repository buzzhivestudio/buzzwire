from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from buzzwire.settings import DATA_DIR, DATABASE_URL, DB_PATH, PAGE_PROFILES_PATH, RSS_FEEDS_PATH


try:
    import psycopg
    from psycopg.rows import dict_row
except Exception:  # pragma: no cover - only needed when DATABASE_URL is postgres.
    psycopg = None
    dict_row = None


DatabaseIntegrityError = (
    (sqlite3.IntegrityError, psycopg.IntegrityError)
    if psycopg is not None
    else (sqlite3.IntegrityError,)
)


def _uses_postgres() -> bool:
    return DATABASE_URL.startswith(("postgres://", "postgresql://"))


def _postgres_url() -> str:
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is required for Postgres mode.")

    # Supabase and most hosted Postgres providers require TLS. Keep local
    # development URLs untouched so docker/local Postgres still works.
    lowered = DATABASE_URL.lower()
    if (
        "sslmode=" not in lowered
        and "localhost" not in lowered
        and "127.0.0.1" not in lowered
    ):
        separator = "&" if "?" in DATABASE_URL else "?"
        return f"{DATABASE_URL}{separator}sslmode=require"
    return DATABASE_URL


def _convert_qmark_placeholders(sql: str) -> str:
    """Convert sqlite-style ? parameters to psycopg %s parameters."""
    output: list[str] = []
    in_single = False
    in_double = False
    index = 0
    while index < len(sql):
        char = sql[index]
        if char == "'" and not in_double:
            output.append(char)
            if in_single and index + 1 < len(sql) and sql[index + 1] == "'":
                output.append(sql[index + 1])
                index += 2
                continue
            in_single = not in_single
            index += 1
            continue
        if char == '"' and not in_single:
            in_double = not in_double
            output.append(char)
            index += 1
            continue
        if char == "?" and not in_single and not in_double:
            output.append("%s")
        else:
            output.append(char)
        index += 1
    return "".join(output)


class PostgresCursor:
    def __init__(self, cursor: Any) -> None:
        self._cursor = cursor
        self.lastrowid: int | None = None

    def fetchone(self) -> dict[str, Any] | None:
        return self._cursor.fetchone()

    def fetchall(self) -> list[dict[str, Any]]:
        return self._cursor.fetchall()


class PostgresConnection:
    backend = "postgres"

    def __init__(self, url: str) -> None:
        if psycopg is None or dict_row is None:
            raise RuntimeError(
                "DATABASE_URL is set to Postgres, but psycopg is not installed. "
                "Run: pip install -r requirements.txt"
            )
        self._conn = psycopg.connect(url, row_factory=dict_row, prepare_threshold=None)

    def execute(self, sql: str, params: Iterable[Any] | None = None) -> PostgresCursor:
        cursor = self._conn.cursor()
        cursor.execute(_convert_qmark_placeholders(sql), tuple(params or ()))
        return PostgresCursor(cursor)

    def executescript(self, sql: str) -> None:
        for statement in (part.strip() for part in sql.split(";")):
            if statement:
                self.execute(statement)

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "PostgresConnection":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        self.close()


def is_postgres(conn: Any) -> bool:
    return getattr(conn, "backend", "sqlite") == "postgres"


def connect(db_path: Path | str = DB_PATH) -> Any:
    if _uses_postgres():
        return PostgresConnection(_postgres_url())

    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS page_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    page_name TEXT NOT NULL UNIQUE,
    username TEXT NOT NULL DEFAULT '',
    niche TEXT NOT NULL,
    audience TEXT NOT NULL,
    emotional_drivers TEXT NOT NULL,
    allowed_topics TEXT NOT NULL,
    blocked_topics TEXT NOT NULL,
    tone_rules TEXT NOT NULL,
    headline_style TEXT NOT NULL,
    caption_style TEXT NOT NULL,
    visual_style TEXT NOT NULL,
    preferred_sources TEXT NOT NULL DEFAULT '[]',
    country_focus TEXT NOT NULL DEFAULT '',
    risk_tolerance TEXT NOT NULL DEFAULT 'medium',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    niche TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS raw_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER,
    input_type TEXT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT NOT NULL DEFAULT '',
    url TEXT,
    published_at TEXT,
    niche_hint TEXT NOT NULL DEFAULT '',
    fetched_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'fetched',
    FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE SET NULL,
    UNIQUE(url)
);

CREATE TABLE IF NOT EXISTS classified_topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_item_id INTEGER NOT NULL UNIQUE,
    categories TEXT NOT NULL,
    country_relevance TEXT NOT NULL,
    emotional_triggers TEXT NOT NULL,
    page_suitability TEXT NOT NULL,
    virality_score REAL NOT NULL,
    risk_level TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (raw_item_id) REFERENCES raw_items(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS generated_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_item_id INTEGER NOT NULL,
    classified_topic_id INTEGER NOT NULL,
    page_profile_id INTEGER NOT NULL,
    neutral_title TEXT NOT NULL,
    viral_title TEXT NOT NULL,
    aggressive_title TEXT NOT NULL,
    caption TEXT NOT NULL,
    carousel_text TEXT NOT NULL,
    visual_direction TEXT NOT NULL,
    suggested_image_keywords TEXT NOT NULL,
    image_brief TEXT NOT NULL DEFAULT '{}',
    risk_notes TEXT NOT NULL,
    source_url TEXT,
    confidence_score REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'generated',
    tone_override TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (raw_item_id) REFERENCES raw_items(id) ON DELETE CASCADE,
    FOREIGN KEY (classified_topic_id) REFERENCES classified_topics(id) ON DELETE CASCADE,
    FOREIGN KEY (page_profile_id) REFERENCES page_profiles(id) ON DELETE CASCADE,
    UNIQUE(raw_item_id, page_profile_id)
);

CREATE TABLE IF NOT EXISTS approvals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    generated_post_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (generated_post_id) REFERENCES generated_posts(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_raw_items_status ON raw_items(status);
CREATE INDEX IF NOT EXISTS idx_generated_posts_status ON generated_posts(status);
"""

POSTGRES_SCHEMA = SQLITE_SCHEMA.replace(
    "INTEGER PRIMARY KEY AUTOINCREMENT",
    "BIGSERIAL PRIMARY KEY",
).replace(
    "source_id INTEGER",
    "source_id BIGINT",
).replace(
    "raw_item_id INTEGER",
    "raw_item_id BIGINT",
).replace(
    "classified_topic_id INTEGER",
    "classified_topic_id BIGINT",
).replace(
    "page_profile_id INTEGER",
    "page_profile_id BIGINT",
).replace(
    "generated_post_id INTEGER",
    "generated_post_id BIGINT",
)


def init_db(conn: Any) -> None:
    if is_postgres(conn):
        conn.executescript(POSTGRES_SCHEMA)
    else:
        conn.executescript(SQLITE_SCHEMA)
    _ensure_column(conn, "page_profiles", "username", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(conn, "page_profiles", "preferred_sources", "TEXT NOT NULL DEFAULT '[]'")
    _ensure_column(conn, "page_profiles", "country_focus", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(conn, "generated_posts", "image_brief", "TEXT NOT NULL DEFAULT '{}'")
    conn.commit()


def _ensure_column(conn: Any, table: str, column: str, column_sql: str) -> None:
    if is_postgres(conn):
        rows = conn.execute(
            """
            SELECT column_name AS name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = ?
            """,
            (table,),
        ).fetchall()
    else:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    if column not in {row["name"] for row in rows}:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_sql}")


def _load_json(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True)


def seed_profiles(conn: Any, path: Path = PAGE_PROFILES_PATH) -> None:
    for profile in _load_json(path):
        conn.execute(
            """
            INSERT INTO page_profiles (
                page_name, username, niche, audience, emotional_drivers, allowed_topics,
                blocked_topics, tone_rules, headline_style, caption_style,
                visual_style, preferred_sources, country_focus, risk_tolerance
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(page_name) DO UPDATE SET
                username = CASE
                    WHEN page_profiles.username = '' THEN excluded.username
                    ELSE page_profiles.username
                END,
                preferred_sources = CASE
                    WHEN excluded.page_name = 'SuccessAddictives' THEN excluded.preferred_sources
                    WHEN page_profiles.preferred_sources IN ('', '[]') THEN excluded.preferred_sources
                    ELSE page_profiles.preferred_sources
                END,
                country_focus = CASE
                    WHEN excluded.page_name = 'SuccessAddictives' THEN excluded.country_focus
                    WHEN page_profiles.country_focus = '' THEN excluded.country_focus
                    ELSE page_profiles.country_focus
                END,
                niche = CASE
                    WHEN excluded.page_name = 'SuccessAddictives' THEN excluded.niche
                    ELSE page_profiles.niche
                END,
                audience = CASE
                    WHEN excluded.page_name = 'SuccessAddictives' THEN excluded.audience
                    ELSE page_profiles.audience
                END,
                emotional_drivers = CASE
                    WHEN excluded.page_name = 'SuccessAddictives' THEN excluded.emotional_drivers
                    ELSE page_profiles.emotional_drivers
                END,
                allowed_topics = CASE
                    WHEN excluded.page_name = 'SuccessAddictives' THEN excluded.allowed_topics
                    ELSE page_profiles.allowed_topics
                END,
                blocked_topics = CASE
                    WHEN excluded.page_name = 'SuccessAddictives' THEN excluded.blocked_topics
                    ELSE page_profiles.blocked_topics
                END,
                tone_rules = CASE
                    WHEN excluded.page_name = 'SuccessAddictives' THEN excluded.tone_rules
                    ELSE page_profiles.tone_rules
                END,
                headline_style = CASE
                    WHEN excluded.page_name = 'SuccessAddictives' THEN excluded.headline_style
                    ELSE page_profiles.headline_style
                END,
                caption_style = CASE
                    WHEN excluded.page_name = 'SuccessAddictives' THEN excluded.caption_style
                    ELSE page_profiles.caption_style
                END,
                visual_style = CASE
                    WHEN excluded.page_name = 'SuccessAddictives' THEN excluded.visual_style
                    ELSE page_profiles.visual_style
                END,
                risk_tolerance = CASE
                    WHEN excluded.page_name = 'SuccessAddictives' THEN excluded.risk_tolerance
                    ELSE page_profiles.risk_tolerance
                END,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                profile["page_name"],
                profile.get("username", ""),
                profile["niche"],
                profile["audience"],
                _dump(profile.get("emotional_drivers", [])),
                _dump(profile.get("allowed_topics", [])),
                _dump(profile.get("blocked_topics", [])),
                profile["tone_rules"],
                profile["headline_style"],
                profile["caption_style"],
                profile["visual_style"],
                _dump(profile.get("preferred_sources", [])),
                profile.get(
                    "country_focus",
                    "India" if profile.get("page_name") == "IndiaPulse" else "Global",
                ),
                profile.get("risk_tolerance", "medium"),
            ),
        )
    conn.commit()


def seed_sources(conn: Any, path: Path = RSS_FEEDS_PATH) -> None:
    for source in _load_json(path):
        conn.execute(
            """
            INSERT INTO sources (name, niche, url, enabled)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                name = excluded.name,
                niche = excluded.niche,
                enabled = excluded.enabled,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                source["name"],
                source["niche"],
                source["url"],
                1 if source.get("enabled", True) else 0,
            ),
        )
    conn.commit()


def initialize_database() -> None:
    if not _uses_postgres():
        DATA_DIR.mkdir(parents=True, exist_ok=True)
    with connect(DB_PATH) as conn:
        init_db(conn)
        seed_profiles(conn)
        seed_sources(conn)
