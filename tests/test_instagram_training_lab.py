from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.instagram_training_lab import (
    analyze_patterns,
    clean_hook_text,
    hook_buckets,
    parse_metric,
    read_examples,
    write_outputs,
)


class InstagramTrainingLabTest(unittest.TestCase):
    def test_parse_metric_supports_social_units(self) -> None:
        self.assertEqual(parse_metric("871K"), 871_000)
        self.assertEqual(parse_metric("54.9M"), 54_900_000)
        self.assertEqual(parse_metric("1.2B"), 1_200_000_000)
        self.assertEqual(parse_metric("12,345"), 12_345)

    def test_hook_buckets_detects_wealth_style_patterns(self) -> None:
        buckets = hook_buckets("The entire world is now $345 trillion in debt, the highest in history")
        self.assertIn("big_number", buckets)
        self.assertIn("ranking", buckets)
        self.assertIn("world_power", buckets)

        culture_buckets = hook_buckets("After 7 years, The Boys will end this week")
        self.assertIn("after_years", culture_buckets)

    def test_clean_hook_text_extracts_instagram_alt_overlay(self) -> None:
        alt = 'Photo by Wealth on May 24, 2026. May be a poster and text that says "Wealth THE 10 RICHEST BANKS IN THE WORLD".'
        self.assertEqual(clean_hook_text(alt), "THE 10 RICHEST BANKS IN THE WORLD")

    def test_outputs_contact_sheet_and_pattern_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            csv_path = base / "examples.csv"
            csv_path.write_text(
                "\n".join(
                    [
                        "post_url,likes,views,hook_text,caption",
                        "https://www.instagram.com/p/one,871K,54.9M,Unlocking a number lock should not be this easy,",
                        "https://www.instagram.com/p/two,10K,120K,Plain update with no hook,",
                    ]
                ),
                encoding="utf-8",
            )
            examples = read_examples(csv_path)
            analysis = analyze_patterns(examples)
            self.assertEqual(analysis["total_examples"], 2)
            self.assertEqual(analysis["top_examples"][0]["views"], 54_900_000)

            out_dir = base / "out"
            write_outputs(examples, out_dir, "views")
            self.assertTrue((out_dir / "contact_sheet_by_views.html").exists())
            self.assertTrue((out_dir / "training_summary.md").exists())
            self.assertTrue((out_dir / "pattern_analysis.json").exists())


if __name__ == "__main__":
    unittest.main()
