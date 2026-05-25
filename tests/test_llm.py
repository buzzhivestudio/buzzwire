from __future__ import annotations

import unittest
from unittest.mock import patch

from buzzwire.services.llm import (
    AnthropicProvider,
    GeminiProvider,
    OpenAIProvider,
    RuleBasedProvider,
    _extract_json_object,
    get_provider,
)


RAW_ITEM = {
    "title": "Google expands AI hiring for engineers",
    "summary": "Google is hiring more artificial intelligence engineers.",
    "url": "https://example.com",
    "niche_hint": "AI jobs",
}

CLASSIFICATION = {
    "categories": ["AI", "business", "jobs"],
    "country_relevance": "Global",
    "emotional_triggers": ["ambition", "fear", "curiosity"],
    "page_suitability": {"SuccessAddictives": 9.0},
    "virality_score": 8.5,
    "risk_level": "low",
}

PROFILE = {
    "id": 1,
    "page_name": "SuccessAddictives",
    "niche": "business, success, AI, jobs, work culture",
    "audience": "Ambitious professionals",
    "emotional_drivers": ["ambition", "fear", "curiosity"],
    "allowed_topics": ["business", "AI", "jobs", "automation"],
    "blocked_topics": [],
    "tone_rules": "dramatic",
    "headline_style": "X is quietly...",
    "caption_style": "business implication",
    "visual_style": "dark corporate",
    "risk_tolerance": "medium",
    "match_score": 8.0,
}


class ModelProviderTest(unittest.TestCase):
    def test_auto_provider_falls_back_to_rule_based_without_keys(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "BUZZWIRE_MODEL_PROVIDER": "auto",
                "OPENAI_API_KEY": "",
                "ANTHROPIC_API_KEY": "",
                "GEMINI_API_KEY": "",
            },
            clear=False,
        ):
            self.assertIsInstance(get_provider(), RuleBasedProvider)

    def test_extract_json_from_code_fence(self) -> None:
        payload = _extract_json_object('```json\n{"viral_title": "Test"}\n```')
        self.assertEqual(payload["viral_title"], "Test")

    def test_openai_response_text_extraction(self) -> None:
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}, clear=False):
            provider = OpenAIProvider()
            with patch(
                "buzzwire.services.llm._request_json",
                return_value={"output_text": '{"viral_title": "OpenAI title"}'},
            ):
                self.assertIn("OpenAI title", provider._complete("prompt"))

    def test_anthropic_response_text_extraction(self) -> None:
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}, clear=False):
            provider = AnthropicProvider()
            with patch(
                "buzzwire.services.llm._request_json",
                return_value={"content": [{"type": "text", "text": '{"viral_title": "Claude title"}'}]},
            ):
                self.assertIn("Claude title", provider._complete("prompt"))

    def test_gemini_response_text_extraction(self) -> None:
        with patch.dict(
            "os.environ",
            {"GEMINI_API_KEY": "test-key", "GEMINI_MODEL": "models/gemini-2.5-flash"},
            clear=False,
        ):
            provider = GeminiProvider()
            with patch(
                "buzzwire.services.llm._request_json",
                return_value={
                    "candidates": [
                        {"content": {"parts": [{"text": '{"viral_title": "Gemini title"}'}]}}
                    ]
                },
            ) as request_json:
                self.assertIn("Gemini title", provider._complete("prompt"))
                self.assertIn("models/gemini-2.5-flash:generateContent", request_json.call_args.args[0])

    def test_api_provider_falls_back_to_rule_based_on_error(self) -> None:
        with patch.dict(
            "os.environ",
            {"OPENAI_API_KEY": "test-key", "BUZZWIRE_FALLBACK_TO_RULE_BASED": "true"},
            clear=False,
        ):
            provider = OpenAIProvider()
            with patch("buzzwire.services.llm.OpenAIProvider._complete", side_effect=RuntimeError("quota")):
                payload = provider.generate_post(RAW_ITEM, CLASSIFICATION, PROFILE)
                self.assertIn("fallback", payload["risk_notes"].lower())
                self.assertIn("Quiet", payload["viral_title"])


if __name__ == "__main__":
    unittest.main()
