from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from buzzwire.db import connect, init_db, seed_profiles
from buzzwire.settings import DB_PATH


def main() -> None:
    with connect(DB_PATH) as conn:
        init_db(conn)
        for table in ("approvals", "generated_posts", "classified_topics", "raw_items", "page_profiles"):
            conn.execute(f"DELETE FROM {table}")
        conn.execute(
            """
            DELETE FROM sqlite_sequence
            WHERE name IN ('approvals', 'generated_posts', 'classified_topics', 'raw_items', 'page_profiles')
            """
        )
        seed_profiles(conn)
        counts = {
            table: conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()["c"]
            for table in ("page_profiles", "raw_items", "classified_topics", "generated_posts", "approvals")
        }
    print(counts)


if __name__ == "__main__":
    main()
