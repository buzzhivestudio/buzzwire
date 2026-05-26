from __future__ import annotations

import unittest

from buzzwire.services.fetcher import rank_rss_items_for_success, score_rss_item_for_success


class FetcherRankingTest(unittest.TestCase):
    def test_success_feed_prefers_wealth_style_hooks_over_routine_news(self) -> None:
        source = {"name": "Mixed Feed", "niche": "business, culture, viral knowledge"}
        items = [
            {
                "title": "Minister meets officials after industry statement",
                "summary": "The meeting focused on routine policy discussion.",
            },
            {
                "title": "The entire world is now $345 trillion in debt, the highest in history",
                "summary": "A new report says global debt reached a record level.",
            },
            {
                "title": "The final episode of The Boys will be 65 minutes long",
                "summary": "The streaming series finale will run longer than usual.",
            },
            {
                "title": "Company appoints new regional advisory panel",
                "summary": "The panel will hold its first hearing next month.",
            },
        ]

        ranked = rank_rss_items_for_success(items, source, limit=2)
        titles = [item["title"] for item in ranked]

        self.assertEqual(
            titles,
            [
                "The entire world is now $345 trillion in debt, the highest in history",
                "The final episode of The Boys will be 65 minutes long",
            ],
        )

    def test_india_national_feed_penalizes_routine_party_politics_for_success_pool(self) -> None:
        source = {"name": "India National", "niche": "India, national"}
        politics = {
            "title": "Rahul and BJP leaders trade remarks after assembly meeting",
            "summary": "Party workers gathered after a minister statement.",
        }
        visual_business = {
            "title": "India's newest airport terminal uses robots to move bags in seconds",
            "summary": "The visual system uses automation and scanners across the building.",
        }

        self.assertGreater(
            score_rss_item_for_success(visual_business, source),
            score_rss_item_for_success(politics, source),
        )

    def test_creator_and_hollywood_sources_lift_public_milestones_not_gossip(self) -> None:
        source = {"name": "Creator Feed", "niche": "influencers, YouTubers, creator economy, Hollywood"}
        creator_milestone = {
            "title": "PewDiePie and Marzia will end family vlogs to protect their son's privacy",
            "summary": "The YouTuber said online content should be the child's choice later in life.",
        }
        gossip = {
            "title": "Celebrity dating rumor splits fans online",
            "summary": "A rumor about a relationship spread on social media.",
        }

        self.assertGreater(
            score_rss_item_for_success(creator_milestone, source),
            score_rss_item_for_success(gossip, source),
        )


if __name__ == "__main__":
    unittest.main()
