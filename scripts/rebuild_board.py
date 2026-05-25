from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

os.environ["BUZZWIRE_MODEL_PROVIDER"] = "rule_based"

from buzzwire.db import connect, init_db
from buzzwire.services.pipeline import process_raw_item
from buzzwire.settings import DB_PATH


def main() -> None:
    with connect(DB_PATH) as conn:
        init_db(conn)
        raw_ids = [
            int(row["id"])
            for row in conn.execute("SELECT id FROM raw_items ORDER BY id").fetchall()
        ]
        conn.execute("DELETE FROM approvals")
        conn.execute("DELETE FROM generated_posts")
        conn.execute("DELETE FROM classified_topics")
        conn.execute(
            """
            DELETE FROM sqlite_sequence
            WHERE name IN ('approvals', 'generated_posts', 'classified_topics')
            """
        )
        for index, raw_id in enumerate(raw_ids):
            process_raw_item(conn, raw_id, variant_hint=index)
        counts = {
            table: conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()["c"]
            for table in ("raw_items", "classified_topics", "generated_posts", "approvals")
        }
    print(counts)


if __name__ == "__main__":
    main()
