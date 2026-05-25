from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from buzzwire import storage
from buzzwire.db import connect, initialize_database
from buzzwire.services.generator import build_angle
from buzzwire.settings import DB_PATH


def main() -> None:
    initialize_database()
    changed = 0
    with connect(DB_PATH) as conn:
        conn.execute(
            "UPDATE generated_posts SET status = 'generated' "
            "WHERE status NOT IN ('generated', 'approved', 'rejected', 'used')"
        )
        conn.commit()
        rows = conn.execute("SELECT id, status FROM generated_posts ORDER BY id").fetchall()
        for row in rows:
            detail = storage.get_generated_post_detail(conn, int(row["id"]))
            raw_item = {
                "id": detail["raw_item_id"],
                "title": detail["topic_title"],
                "summary": detail["topic_summary"],
                "url": detail["topic_url"],
                "niche_hint": detail["niche_hint"],
            }
            classification = {
                "categories": detail["categories"],
                "country_relevance": detail["country_relevance"],
                "emotional_triggers": detail["emotional_triggers"],
                "page_suitability": detail["page_suitability"],
                "virality_score": detail["virality_score"],
                "risk_level": detail["risk_level"],
            }
            profile = {
                "id": detail["page_profile_id"],
                "page_name": detail["page_name"],
                "niche": detail["niche"],
                "audience": detail["audience"],
                "emotional_drivers": detail["emotional_drivers"],
                "allowed_topics": detail["allowed_topics"],
                "blocked_topics": detail["blocked_topics"],
                "tone_rules": detail["tone_rules"],
                "headline_style": detail["headline_style"],
                "caption_style": detail["caption_style"],
                "visual_style": detail["visual_style"],
                "preferred_sources": detail.get("preferred_sources", []),
                "country_focus": detail.get("country_focus", ""),
                "risk_tolerance": detail["risk_tolerance"],
                "match_score": detail["page_suitability"].get(detail["page_name"], 4.0),
            }
            payload = build_angle(raw_item, classification, profile, variant_hint=int(row["id"]))
            if row["status"] in {"approved", "used"}:
                fields = {
                    "confidence_score": payload["confidence_score"],
                    "image_brief": payload["image_brief"],
                    "source_url": payload.get("source_url"),
                }
            else:
                fields = dict(payload)
            storage.update_generated_post_fields(conn, int(row["id"]), fields)
            changed += 1
    print(f"normalized {changed} generated posts")


if __name__ == "__main__":
    main()
