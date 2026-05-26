from __future__ import annotations

import unittest

from buzzwire.services.classifier import classify_topic
from buzzwire.services.generator import build_angle
from buzzwire.services.matcher import match_pages


PROFILES = [
    {
        "id": 1,
        "page_name": "SuccessAddictives",
        "niche": "business, success, AI, jobs, work culture",
        "audience": "Ambitious professionals",
        "emotional_drivers": ["ambition", "fear", "curiosity"],
        "allowed_topics": ["business", "AI", "jobs", "automation", "work culture"],
        "blocked_topics": ["celebrity gossip"],
        "tone_rules": "dramatic",
        "headline_style": "X is quietly...",
        "caption_style": "business implication",
        "visual_style": "dark corporate",
        "risk_tolerance": "medium",
    },
    {
        "id": 2,
        "page_name": "IndiaPulse",
        "niche": "India, economy, geopolitics, infrastructure, culture, tech",
        "audience": "Young Indians",
        "emotional_drivers": ["nationalism", "curiosity", "pride", "urgency"],
        "allowed_topics": ["India", "economy", "technology", "infrastructure"],
        "blocked_topics": ["communal hate"],
        "tone_rules": "bold",
        "headline_style": "India just...",
        "caption_style": "national relevance",
        "visual_style": "clean news",
        "risk_tolerance": "medium",
    },
    {
        "id": 3,
        "page_name": "CEOBeingCEO",
        "niche": "CEO, founders, business, leadership, money, productivity, startups, AI, work culture",
        "audience": "Ambitious operators",
        "emotional_drivers": ["ambition", "authority", "curiosity", "urgency", "status"],
        "allowed_topics": ["business", "startups", "leadership", "money", "AI", "jobs", "productivity"],
        "blocked_topics": ["party politics", "celebrity gossip"],
        "tone_rules": "executive and strategic",
        "headline_style": "CEOs are quietly...",
        "caption_style": "business lesson",
        "visual_style": "premium business",
        "risk_tolerance": "medium",
    },
]


class PipelineHeuristicsTest(unittest.TestCase):
    def test_ai_jobs_topic_matches_success_page(self) -> None:
        raw_item = {
            "title": "Google expands AI hiring for engineers",
            "summary": "Google is hiring more artificial intelligence engineers as companies automate work.",
            "niche_hint": "AI jobs",
        }
        classification = classify_topic(raw_item)
        matches, suitability = match_pages(PROFILES, classification, raw_item)
        classification["page_suitability"] = suitability

        self.assertIn("AI", classification["categories"])
        self.assertNotIn("geopolitics", classification["categories"])
        self.assertGreaterEqual(classification["virality_score"], 7)
        self.assertIn("SuccessAddictives", [match["page_name"] for match in matches])

        success_match = next(match for match in matches if match["page_name"] == "SuccessAddictives")
        payload = build_angle(raw_item, classification, success_match)
        self.assertIn("Quiet", payload["viral_title"])
        self.assertIn("future of work", payload["caption"].lower())
        self.assertGreaterEqual(payload["confidence_score"], 1)
        self.assertLessEqual(payload["confidence_score"], 10)
        self.assertIn("composition", payload["image_brief"])

    def test_entry_level_jobs_story_matches_business_pages(self) -> None:
        raw_item = {
            "title": "Next boss warns of 'dramatic' fall in entry-level jobs",
            "summary": "A company boss warned that entry-level jobs are shrinking as businesses change hiring plans.",
            "niche_hint": "",
        }
        classification = classify_topic(raw_item)
        matches, suitability = match_pages(PROFILES, classification, raw_item)
        matched_pages = [match["page_name"] for match in matches]

        self.assertIn("business", classification["categories"])
        self.assertIn("jobs", classification["categories"])
        self.assertIn("fear", classification["emotional_triggers"])
        self.assertIn("SuccessAddictives", matched_pages)
        self.assertIn("CEOBeingCEO", matched_pages)
        self.assertGreaterEqual(suitability["CEOBeingCEO"], 5.0)

    def test_successaddictives_gets_visual_engineering_explainers(self) -> None:
        raw_item = {
            "title": "Novel origami pattern turns flat sheets into load-bearing 3D technology",
            "summary": "Engineers developed a folding pattern that turns flexible sheets into stiff structures on demand.",
            "niche_hint": "engineering visual explainer innovation",
        }
        classification = classify_topic(raw_item)
        matches, suitability = match_pages(PROFILES, classification, raw_item)
        matched_pages = [match["page_name"] for match in matches]

        self.assertIn("engineering", classification["categories"])
        self.assertIn("visual_explainer", classification["categories"])
        self.assertIn("SuccessAddictives", matched_pages)
        self.assertNotIn("CEOBeingCEO", matched_pages)
        self.assertGreaterEqual(suitability["SuccessAddictives"], 5.0)

        success_match = next(match for match in matches if match["page_name"] == "SuccessAddictives")
        payload = build_angle(raw_item, classification, success_match)
        self.assertIn("Engineering", payload["viral_title"])
        self.assertIn("mechanism", payload["caption"].lower())
        self.assertNotIn("future of work", payload["caption"].lower())
        self.assertIn("How it works", payload["image_brief"]["possible_overlays"])
        self.assertIn("engineering close-up", payload["suggested_image_keywords"])

    def test_successaddictives_gets_wealth_style_culture_stories(self) -> None:
        raw_item = {
            "title": "The final episode of The Boys will be 65 minutes long",
            "summary": "The streaming series finale will run longer than a normal episode.",
            "niche_hint": "entertainment culture viral knowledge",
        }
        classification = classify_topic(raw_item)
        matches, suitability = match_pages(PROFILES, classification, raw_item)
        matched_pages = [match["page_name"] for match in matches]

        self.assertIn("entertainment", classification["categories"])
        self.assertIn("SuccessAddictives", matched_pages)
        self.assertNotIn("CEOBeingCEO", matched_pages)
        self.assertGreaterEqual(suitability["SuccessAddictives"], 5.0)

        success_match = next(match for match in matches if match["page_name"] == "SuccessAddictives")
        payload = build_angle(raw_item, classification, success_match)
        self.assertEqual(payload["viral_title"], "The Final Episode Of The Boys Will Be 65 Minutes Long")
        self.assertNotIn("Bigger Than It Looks", payload["viral_title"])
        self.assertIn("visual fact", payload["caption"].lower())
        self.assertIn("yellow headline", payload["suggested_image_keywords"])
        self.assertIn("circle inset", payload["image_brief"]["possible_overlays"])

    def test_successaddictives_gets_wealth_style_world_money_stories(self) -> None:
        raw_item = {
            "title": "The entire world is now $345 trillion in debt, the highest in history",
            "summary": "Global debt has reached a record level according to a new report.",
            "niche_hint": "money geopolitics viral knowledge",
        }
        classification = classify_topic(raw_item)
        matches, suitability = match_pages(PROFILES, classification, raw_item)
        matched_pages = [match["page_name"] for match in matches]

        self.assertIn("money", classification["categories"])
        self.assertIn("history", classification["categories"])
        self.assertIn("SuccessAddictives", matched_pages)
        self.assertGreaterEqual(suitability["SuccessAddictives"], 5.0)

        success_match = next(match for match in matches if match["page_name"] == "SuccessAddictives")
        payload = build_angle(raw_item, classification, success_match)
        self.assertEqual(
            payload["viral_title"],
            "The Entire World Is Now $345 Trillion In Debt, The Highest In History",
        )
        self.assertNotIn("Bigger Than", payload["viral_title"])
        self.assertIn("source-led", payload["caption"].lower())
        self.assertIn("big number", payload["image_brief"]["possible_overlays"])

    def test_successaddictives_gets_creator_and_influencer_stories(self) -> None:
        raw_item = {
            "title": "PewDiePie and Marzia will end their family vlogs to protect their son Bjorn's privacy",
            "summary": "The YouTuber said future online content should be his child's choice later in life.",
            "niche_hint": "influencers YouTubers creator economy viral internet culture",
        }
        classification = classify_topic(raw_item)
        matches, suitability = match_pages(PROFILES, classification, raw_item)
        matched_pages = [match["page_name"] for match in matches]

        self.assertIn("influencers", classification["categories"])
        self.assertIn("SuccessAddictives", matched_pages)
        self.assertNotIn("CEOBeingCEO", matched_pages)
        self.assertGreaterEqual(suitability["SuccessAddictives"], 5.0)

        success_match = next(match for match in matches if match["page_name"] == "SuccessAddictives")
        payload = build_angle(raw_item, classification, success_match)
        self.assertIn("PewDiePie", payload["viral_title"])
        self.assertNotIn("Bigger Than It Looks", payload["viral_title"])
        self.assertIn("creator", payload["caption"].lower())
        self.assertIn("privacy", payload["caption"].lower())

    def test_title_casing_preserves_common_ai_branding(self) -> None:
        raw_item = {
            "title": "OpenAI launches API tools for AI agents",
            "summary": "OpenAI launched new tools for developers.",
            "niche_hint": "AI business",
        }
        classification = classify_topic(raw_item)
        matches, suitability = match_pages(PROFILES, classification, raw_item)
        classification["page_suitability"] = suitability

        payload = build_angle(raw_item, classification, matches[0])
        self.assertEqual(payload["neutral_title"], "OpenAI Launches API Tools For AI Agents")

    def test_india_topic_matches_india_page(self) -> None:
        raw_item = {
            "title": "India opens new semiconductor manufacturing hub",
            "summary": "India announced a new factory plan to grow technology manufacturing.",
            "niche_hint": "India economy tech",
        }
        classification = classify_topic(raw_item)
        matches, suitability = match_pages(PROFILES, classification, raw_item)
        classification["page_suitability"] = suitability

        self.assertEqual(classification["country_relevance"], "India")
        self.assertEqual(matches[0]["page_name"], "IndiaPulse")
        payload = build_angle(raw_item, classification, matches[0])
        self.assertIn("India", payload["viral_title"])

    def test_indian_party_politics_only_matches_india_page(self) -> None:
        raw_item = {
            "title": "Modi, Shah are traitors who are attacking the Constitution, says Rahul at Rae Bareli meet",
            "summary": "Congress leader says that the BJP government is trying to do away with reservation given for marginalised sections",
            "niche_hint": "",
        }
        classification = classify_topic(raw_item)
        matches, suitability = match_pages(PROFILES, classification, raw_item)
        classification["page_suitability"] = suitability

        self.assertIn("domestic_politics", classification["categories"])
        self.assertEqual(classification["risk_level"], "high")
        self.assertEqual([match["page_name"] for match in matches], ["IndiaPulse"])
        self.assertEqual(suitability["SuccessAddictives"], 0.0)

        payload = build_angle(raw_item, classification, matches[0])
        self.assertIn("Sparks Debate", payload["viral_title"])
        self.assertIn("alleged", payload["caption"].lower())
        self.assertIn("allegation", payload["caption"].lower())
        self.assertNotIn("future of work", payload["caption"].lower())
        self.assertIn("High risk politics", payload["risk_notes"])
        self.assertIn("Verify source", payload["image_brief"]["possible_overlays"])

    def test_india_foreign_policy_with_modi_is_not_domestic_politics(self) -> None:
        raw_item = {
            "title": "Norway foreign minister says India and Norway should reduce trade dependence",
            "summary": "In an interview after Modi bilateral talks, Norway's foreign minister discussed global powers and technology trade.",
            "niche_hint": "India, national",
        }
        classification = classify_topic(raw_item)

        self.assertIn("India", classification["categories"])
        self.assertNotIn("domestic_politics", classification["categories"])

    def test_success_page_does_not_call_country_only_topic_an_india_move(self) -> None:
        raw_item = {
            "title": "Google rejects UK union recognition but offers talks",
            "summary": "The move opens a formal window for talks on recognition.",
            "niche_hint": "India, technology, startups",
        }
        classification = classify_topic(raw_item)
        profile = dict(PROFILES[0])
        profile["match_score"] = 4.0
        payload = build_angle(raw_item, classification, profile, variant_hint=2)

        self.assertNotIn("India Move", payload["viral_title"])
        self.assertNotIn("India race", payload["caption"])

    def test_tight_headlines_avoid_general_and_bad_possessives(self) -> None:
        raw_item = {
            "title": "Supermarkets hit back over pressure to cap prices",
            "summary": "Supermarkets pushed back after pressure to cap milk and bread prices.",
            "niche_hint": "business",
        }
        classification = classify_topic(raw_item)
        profile = dict(PROFILES[0])
        profile["match_score"] = 4.0
        payload = build_angle(raw_item, classification, profile)

        self.assertIn("Supermarkets Are", payload["viral_title"])
        self.assertNotIn("Supermarkets Is", payload["viral_title"])
        self.assertNotIn("General", payload["viral_title"])

    def test_success_headline_does_not_repeat_same_actor_and_topic(self) -> None:
        raw_item = {
            "title": "AI helping engineering hubs generate IP faster",
            "summary": "AI tools are helping engineering hubs move faster.",
            "niche_hint": "AI business",
        }
        classification = classify_topic(raw_item)
        profile = dict(PROFILES[0])
        profile["match_score"] = 5.0
        payload = build_angle(raw_item, classification, profile)

        self.assertNotIn("AI Bet", payload["viral_title"])
        self.assertIn("IP", payload["viral_title"])

    def test_ceo_ai_titles_are_source_specific_not_repeated(self) -> None:
        profile = dict(PROFILES[2])
        profile["match_score"] = 7.0
        raw_items = [
            {
                "title": "AI helping engineering hubs generate IP faster",
                "summary": "AI tools are helping engineering hubs move faster.",
                "niche_hint": "AI business",
            },
            {
                "title": "OpenAI launches API tools for AI agents",
                "summary": "OpenAI launched new tools for developers.",
                "niche_hint": "AI business",
            },
            {
                "title": "Microsoft says AI agents are changing work",
                "summary": "Microsoft says agents are becoming part of the workplace.",
                "niche_hint": "AI jobs",
            },
        ]
        titles = []
        for raw_item in raw_items:
            classification = classify_topic(raw_item)
            titles.append(build_angle(raw_item, classification, profile, variant_hint=4)["viral_title"])

        self.assertEqual(len(set(titles)), len(titles))
        self.assertNotIn("The AI Race CEOs Should Be Watching", titles)
        self.assertTrue(any("API Tools" in title for title in titles))
        self.assertTrue(any("Microsoft" in title for title in titles))

    def test_ceo_page_has_specific_titles_not_story_placeholders(self) -> None:
        raw_item = {
            "title": "SpaceX files for IPO that could make Elon Musk a trillionaire",
            "summary": "The company is preparing a public listing that could reshape founder wealth.",
            "niche_hint": "business",
        }
        classification = classify_topic(raw_item)
        profile = dict(PROFILES[2])
        profile["match_score"] = 7.0
        payload = build_angle(raw_item, classification, profile)

        self.assertIn("IPO", payload["viral_title"])
        self.assertNotIn("Story Story", payload["viral_title"])
        self.assertNotIn("Bigger Than It Looks", payload["viral_title"])
        self.assertIn("CEO angle", payload["caption"])

    def test_trinamool_assembly_protest_is_politics_not_ceo_content(self) -> None:
        raw_item = {
            "title": "Trinamool MLAs hold protest in West Bengal Assembly over hawker eviction and torture against party workers",
            "summary": "Senior leaders led a sit-in demonstration inside the Assembly compound.",
            "niche_hint": "India, national",
        }
        classification = classify_topic(raw_item)
        matches, suitability = match_pages(PROFILES, classification, raw_item)

        self.assertIn("domestic_politics", classification["categories"])
        self.assertEqual(classification["risk_level"], "high")
        self.assertEqual([match["page_name"] for match in matches], ["IndiaPulse"])
        self.assertEqual(suitability["CEOBeingCEO"], 0.0)
        self.assertEqual(suitability["SuccessAddictives"], 0.0)


if __name__ == "__main__":
    unittest.main()
