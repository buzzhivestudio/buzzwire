from __future__ import annotations

import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from abc import ABC, abstractmethod
from typing import Any

from buzzwire.services.generator import build_angle


REQUIRED_PAYLOAD_KEYS = {
    "neutral_title",
    "viral_title",
    "aggressive_title",
    "caption",
    "carousel_text",
    "visual_direction",
    "suggested_image_keywords",
    "image_brief",
    "risk_notes",
    "source_url",
    "confidence_score",
}

GENERIC_TITLE_PHRASES = {
    "story story",
    "story gets bigger",
    "bigger than it looks",
    "bigger than a normal headline",
    "real business angle here",
    "real geopolitics angle here",
    "ai race ceos should be watching",
    "this story is bigger",
    "this could change everything",
}


def _generic_title(value: Any) -> bool:
    title = str(value or "").strip().lower()
    if not title:
        return True
    return any(phrase in title for phrase in GENERIC_TITLE_PHRASES)


class ModelProvider(ABC):
    name: str

    @abstractmethod
    def generate_post(
        self,
        raw_item: dict[str, Any],
        classification: dict[str, Any],
        profile: dict[str, Any],
        *,
        variant_hint: int = 0,
        tone_override: str | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError


class RuleBasedProvider(ModelProvider):
    name = "rule_based"

    def generate_post(
        self,
        raw_item: dict[str, Any],
        classification: dict[str, Any],
        profile: dict[str, Any],
        *,
        variant_hint: int = 0,
        tone_override: str | None = None,
    ) -> dict[str, Any]:
        return build_angle(
            raw_item,
            classification,
            profile,
            variant_hint=variant_hint,
            tone_override=tone_override,
        )


def _timeout() -> float:
    return float(os.getenv("BUZZWIRE_API_TIMEOUT", "30"))


def _request_json(url: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urlopen(request, timeout=_timeout()) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Model API returned {exc.code}: {body[:500]}") from exc
    except URLError as exc:
        raise RuntimeError(f"Model API request failed: {exc.reason}") from exc


def _extract_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if not match:
            raise
        return json.loads(match.group(0))


def _as_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [line.strip(" -") for line in value.splitlines() if line.strip(" -")]
    return []


def _as_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _merge_payload(base: dict[str, Any], generated: dict[str, Any]) -> dict[str, Any]:
    merged = {**base}
    for key in REQUIRED_PAYLOAD_KEYS:
        if key in generated and generated[key] not in (None, ""):
            merged[key] = generated[key]
    for title_key in ("viral_title", "aggressive_title"):
        if _generic_title(merged.get(title_key)):
            merged[title_key] = base[title_key]
    merged["carousel_text"] = _as_string_list(merged.get("carousel_text")) or base["carousel_text"]
    merged["suggested_image_keywords"] = (
        _as_string_list(merged.get("suggested_image_keywords")) or base["suggested_image_keywords"]
    )
    merged["image_brief"] = _as_object(merged.get("image_brief")) or base["image_brief"]
    try:
        merged["confidence_score"] = round(float(merged.get("confidence_score", base["confidence_score"])), 1)
    except (TypeError, ValueError):
        merged["confidence_score"] = base["confidence_score"]
    if merged["confidence_score"] <= 1:
        merged["confidence_score"] *= 10
    merged["confidence_score"] = round(max(1.0, min(10.0, merged["confidence_score"])), 1)
    return merged


def _fallback_enabled() -> bool:
    return os.getenv("BUZZWIRE_FALLBACK_TO_RULE_BASED", "true").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _short_error(exc: Exception) -> str:
    message = str(exc).split("{", 1)[0].strip()
    return message[:180] or exc.__class__.__name__


def _prompt_for_angle(
    raw_item: dict[str, Any],
    classification: dict[str, Any],
    profile: dict[str, Any],
    base: dict[str, Any],
    tone_override: str | None,
) -> str:
    style_training_notes = ""
    if profile.get("page_name") == "SuccessAddictives":
        style_training_notes = (
            "Use SuccessAddictives/Pubity/@wealth-style concrete hooks: exact names, numbers, dates, public creator moves, "
            "celebrity career milestones, money/status signals, rankings, first-ever claims, and visual facts. "
            "Good examples: 'PEWDIEPIE AND MARZIA WILL END THEIR FAMILY VLOGS TO PROTECT THEIR SON'S PRIVACY', "
            "'ELON MUSK WILL LIKELY BECOME THE WORLD'S FIRST TRILLIONAIRE THIS YEAR', 'WHEN DID THE WORLD LOSE ITS COLOR', "
            "'THE RICHEST PEOPLE TO HAVE EVER LIVED', '2027 IS ALREADY SHAPING UP TO BE A MASSIVE YEAR FOR MOVIES', "
            "'THE ENTIRE WORLD IS NOW $345 TRILLION IN DEBT'. Avoid generic titles like 'this story is bigger than it looks', "
            "'story gets bigger', 'the real angle here', or vague AI/business placeholders. Avoid cheap celebrity gossip; frame public "
            "creator/celebrity stories as career, privacy, money, legacy, or culture signals."
        )
    elif profile.get("page_name") == "CEOBeingCEO":
        style_training_notes = (
            "Use source-specific executive hooks. Mention the company, CEO, deal, job, IPO, product, or money detail. "
            "Avoid generic placeholders like 'the AI race CEOs should be watching' unless the source itself is about a specific AI race."
        )
    context = {
        "task": "Turn a raw news item into a page-specific viral Instagram content angle.",
        "important_rule": "Do not make a generic summary. Make the angle fit the exact page profile.",
        "style_training_notes": style_training_notes,
        "page_profile": {
            "page_name": profile.get("page_name"),
            "username": profile.get("username"),
            "niche": profile.get("niche"),
            "audience": profile.get("audience"),
            "emotional_drivers": profile.get("emotional_drivers", []),
            "allowed_topics": profile.get("allowed_topics", []),
            "blocked_topics": profile.get("blocked_topics", []),
            "tone_rules": profile.get("tone_rules"),
            "headline_style": profile.get("headline_style"),
            "caption_style": profile.get("caption_style"),
            "visual_style": profile.get("visual_style"),
            "preferred_sources": profile.get("preferred_sources", []),
            "country_focus": profile.get("country_focus"),
            "risk_tolerance": profile.get("risk_tolerance"),
        },
        "raw_item": {
            "title": raw_item.get("title"),
            "summary": raw_item.get("summary"),
            "source_url": raw_item.get("url"),
            "niche_hint": raw_item.get("niche_hint"),
        },
        "classification": classification,
        "tone_override": tone_override,
        "baseline_to_improve": base,
        "required_json_keys": sorted(REQUIRED_PAYLOAD_KEYS),
    }
    return (
        "Return only a valid JSON object. Keep claims source-led, avoid hate/harassment, "
        "avoid definitive claims that are not in the source, and keep Instagram copy punchy.\n\n"
        f"{json.dumps(context, ensure_ascii=True, indent=2)}"
    )


class ApiProvider(ModelProvider):
    env_key = ""
    provider_label = ""
    model_env_key = ""
    default_model = ""

    def __init__(self) -> None:
        self.api_key = os.getenv(self.env_key, "")
        self.model = os.getenv(self.model_env_key, self.default_model)

    def _complete(self, prompt: str) -> str:
        raise NotImplementedError

    def generate_post(
        self,
        raw_item: dict[str, Any],
        classification: dict[str, Any],
        profile: dict[str, Any],
        *,
        variant_hint: int = 0,
        tone_override: str | None = None,
    ) -> dict[str, Any]:
        if not self.api_key:
            raise RuntimeError(f"{self.env_key} is not set. Add it to .env or use rule_based.")
        base = build_angle(
            raw_item,
            classification,
            profile,
            variant_hint=variant_hint,
            tone_override=tone_override,
        )
        prompt = _prompt_for_angle(raw_item, classification, profile, base, tone_override)
        try:
            generated = _extract_json_object(self._complete(prompt))
        except Exception as exc:
            if not _fallback_enabled():
                raise
            base["risk_notes"] = (
                f"{base['risk_notes']} AI provider fallback used because {self.provider_label} failed: "
                f"{_short_error(exc)}."
            )
            return base
        return _merge_payload(base, generated)


class OpenAIProvider(ApiProvider):
    name = "openai"
    env_key = "OPENAI_API_KEY"
    model_env_key = "OPENAI_MODEL"
    default_model = "gpt-5"
    provider_label = "OpenAI"

    def _complete(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "instructions": "You are BuzzWire's viral Instagram news angle engine. Return only valid JSON.",
            "input": prompt,
            "max_output_tokens": 1400,
        }
        data = _request_json(
            "https://api.openai.com/v1/responses",
            payload,
            {"Authorization": f"Bearer {self.api_key}"},
        )
        if data.get("output_text"):
            return str(data["output_text"])
        for item in data.get("output", []):
            for content in item.get("content", []):
                if content.get("type") in {"output_text", "text"} and content.get("text"):
                    return str(content["text"])
        raise RuntimeError("OpenAI response did not contain text output.")


class AnthropicProvider(ApiProvider):
    name = "anthropic"
    env_key = "ANTHROPIC_API_KEY"
    model_env_key = "ANTHROPIC_MODEL"
    default_model = "claude-sonnet-4-20250514"
    provider_label = "Claude"

    def _complete(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "max_tokens": 1400,
            "system": "You are BuzzWire's viral Instagram news angle engine. Return only valid JSON.",
            "messages": [{"role": "user", "content": prompt}],
        }
        data = _request_json(
            "https://api.anthropic.com/v1/messages",
            payload,
            {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
        )
        chunks = [
            str(part.get("text", ""))
            for part in data.get("content", [])
            if part.get("type") == "text" and part.get("text")
        ]
        if chunks:
            return "".join(chunks)
        raise RuntimeError("Anthropic response did not contain text output.")


class GeminiProvider(ApiProvider):
    name = "gemini"
    env_key = "GEMINI_API_KEY"
    model_env_key = "GEMINI_MODEL"
    default_model = "gemini-2.5-flash"
    provider_label = "Gemini"

    def _complete(self, prompt: str) -> str:
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": (
                                "You are BuzzWire's viral Instagram news angle engine. "
                                "Return only valid JSON.\n\n"
                                f"{prompt}"
                            )
                        }
                    ],
                }
            ],
            "generationConfig": {"responseMimeType": "application/json"},
        }
        model = quote(self.model.removeprefix("models/"), safe="")
        data = _request_json(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}",
            payload,
            {},
        )
        parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        chunks = [str(part.get("text", "")) for part in parts if part.get("text")]
        if chunks:
            return "".join(chunks)
        raise RuntimeError("Gemini response did not contain text output.")


def provider_status() -> dict[str, Any]:
    selected = os.getenv("BUZZWIRE_MODEL_PROVIDER", "rule_based").strip().lower()
    availability = {
        "openai": bool(os.getenv("OPENAI_API_KEY")),
        "anthropic": bool(os.getenv("ANTHROPIC_API_KEY")),
        "gemini": bool(os.getenv("GEMINI_API_KEY")),
        "rule_based": True,
    }
    active = get_provider(selected).name
    return {
        "selected": selected,
        "active": active,
        "available": availability,
        "models": {
            "openai": os.getenv("OPENAI_MODEL", OpenAIProvider.default_model),
            "anthropic": os.getenv("ANTHROPIC_MODEL", AnthropicProvider.default_model),
            "gemini": os.getenv("GEMINI_MODEL", GeminiProvider.default_model),
        },
    }


def get_provider(name: str | None = None) -> ModelProvider:
    selected = (name or os.getenv("BUZZWIRE_MODEL_PROVIDER", "rule_based")).strip().lower()
    if selected == "auto":
        if os.getenv("OPENAI_API_KEY"):
            selected = "openai"
        elif os.getenv("ANTHROPIC_API_KEY"):
            selected = "anthropic"
        elif os.getenv("GEMINI_API_KEY"):
            selected = "gemini"
        else:
            selected = "rule_based"
    providers: dict[str, type[ModelProvider]] = {
        "rule_based": RuleBasedProvider,
        "mock": RuleBasedProvider,
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "claude": AnthropicProvider,
        "gemini": GeminiProvider,
    }
    provider_cls = providers.get(selected)
    if provider_cls is None:
        raise ValueError(f"Unknown model provider: {selected}")
    return provider_cls()
