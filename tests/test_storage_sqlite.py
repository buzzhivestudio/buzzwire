from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from buzzwire import storage
from buzzwire.db import connect, init_db, seed_profiles


class StorageSqliteTest(unittest.TestCase):
    def test_sqlite_storage_round_trip_still_works(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "buzzwire.db"
            conn = connect(db_path)
            try:
                init_db(conn)
                seed_profiles(conn)

                raw_id = storage.insert_raw_item(
                    conn,
                    source_id=None,
                    input_type="manual",
                    title="Google expands AI engineering hiring",
                    summary="Google is adding more AI roles.",
                    url="https://example.com/google-ai-hiring",
                    niche_hint="AI jobs",
                )
                classification_id = storage.save_classification(
                    conn,
                    raw_id,
                    {
                        "categories": ["AI", "jobs"],
                        "country_relevance": "Global",
                        "emotional_triggers": ["curiosity"],
                        "page_suitability": {"SuccessAddictives": 8.0},
                        "virality_score": 7.5,
                        "risk_level": "low",
                    },
                )
                profile = storage.get_profiles(conn)[0]
                post_id = storage.save_generated_post(
                    conn,
                    raw_item_id=raw_id,
                    classified_topic_id=classification_id,
                    page_profile_id=int(profile["id"]),
                    payload={
                        "neutral_title": "Google Expands AI Engineering Hiring",
                        "viral_title": "Google Is Quietly Building The Future Of Work",
                        "aggressive_title": "Google Is Quietly Coming For Your Job",
                        "caption": "A compact test caption.",
                        "carousel_text": ["Slide 1", "Slide 2"],
                        "visual_direction": "Dark newsroom visual.",
                        "suggested_image_keywords": ["Google", "AI"],
                        "image_brief": {"mood": "focused"},
                        "risk_notes": "Low risk.",
                        "source_url": "https://example.com/google-ai-hiring",
                        "confidence_score": 8.2,
                    },
                )

                detail = storage.get_generated_post_detail(conn, post_id)
                self.assertEqual(detail["raw_item_id"], raw_id)
                self.assertEqual(detail["classified_topic_id"], classification_id)
                self.assertEqual(detail["carousel_text"], ["Slide 1", "Slide 2"])
                self.assertEqual(detail["image_brief"], {"mood": "focused"})

                same_post_id = storage.save_generated_post(
                    conn,
                    raw_item_id=raw_id,
                    classified_topic_id=classification_id,
                    page_profile_id=int(profile["id"]),
                    payload={
                        "neutral_title": "Google Expands AI Engineering Hiring",
                        "viral_title": "Google's AI Hiring Race Is Getting Sharper",
                        "aggressive_title": "Why Google's AI Hiring Matters For Workers",
                        "caption": "A refreshed generated caption.",
                        "carousel_text": ["New Slide"],
                        "visual_direction": "Updated visual.",
                        "suggested_image_keywords": ["Google", "AI", "hiring"],
                        "image_brief": {"mood": "updated"},
                        "risk_notes": "Low risk.",
                        "source_url": "https://example.com/google-ai-hiring",
                        "confidence_score": 8.8,
                    },
                )

                refreshed = storage.get_generated_post_detail(conn, same_post_id)
                self.assertEqual(same_post_id, post_id)
                self.assertEqual(refreshed["viral_title"], "Google's AI Hiring Race Is Getting Sharper")
                self.assertEqual(refreshed["caption"], "A refreshed generated caption.")
            finally:
                conn.close()


if __name__ == "__main__":
    unittest.main()
