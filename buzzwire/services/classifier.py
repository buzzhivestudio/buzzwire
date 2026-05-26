from __future__ import annotations

import re
from typing import Any


CATEGORY_KEYWORDS = {
    "AI": [
        "ai",
        "artificial intelligence",
        "machine learning",
        "automation",
        "robot",
        "chatbot",
        "openai",
        "gemini",
        "smart glasses",
        "software",
        "ip",
    ],
    "business": [
        "business",
        "boss",
        "company",
        "executive",
        "startup",
        "funding",
        "market",
        "stock",
        "stocks",
        "profit",
        "revenue",
        "ceo",
        "hiring",
        "ipo",
        "trade deal",
        "deal",
        "union",
        "recognition",
        "restructuring",
        "loss",
        "price",
        "prices",
        "grant",
        "investment",
        "investor",
        "spending",
    ],
    "jobs": [
        "job",
        "jobs",
        "entry-level",
        "entry level",
        "career",
        "workforce",
        "layoff",
        "salary",
        "employee",
        "workplace",
        "engineer",
        "manager",
        "graduate jobs",
    ],
    "India": ["india", "indian", "delhi", "mumbai", "bengaluru", "rupee", "modi", "bharat", "bjp", "congress"],
    "domestic_politics": [
        "bjp",
        "congress",
        "rahul",
        "amit shah",
        "constitution",
        "reservation",
        "election",
        "parliament",
        "lok sabha",
        "rajya sabha",
        "party politics",
        "political party",
        "opposition",
        "trinamool",
        "tmc",
        "mla",
        "mlas",
        "assembly",
        "party workers",
        "sit-in",
        "protest",
        "traitor",
        "traitors",
        "attacking the constitution",
        "political",
    ],
    "geopolitics": ["china", "russia", "us", "usa", "trade", "border", "war", "defense", "sanction", "geopolitics"],
    "infrastructure": ["rail", "road", "airport", "port", "bridge", "metro", "infrastructure", "highway", "factory"],
    "engineering": [
        "engineering",
        "engineered",
        "mechanism",
        "mechanical",
        "physics",
        "pipe",
        "plumbing",
        "sealant",
        "wrench",
        "tool",
        "construction",
        "repair",
        "prototype",
        "design",
        "industrial",
        "material",
        "materials",
        "robotics",
        "drone",
        "scanner",
        "sensor",
        "motor",
        "battery",
        "vehicle",
        "car",
        "automotive",
        "origami",
        "load-bearing",
        "3d printing",
        "3d technology",
        "solar cell",
        "solar cells",
        "perovskite",
        "alloy",
        "chip",
        "hardware",
        "device",
    ],
    "visual_explainer": [
        "how it works",
        "why it works",
        "looks impossible",
        "most people",
        "no idea",
        "never realize",
        "hidden",
        "simple trick",
        "this method",
        "this process",
        "this system",
        "this tool",
        "in seconds",
        "without digging",
        "without a shovel",
        "changes everything",
        "pure physics",
        "turns flat",
        "turn flat",
        "before and after",
        "step-by-step",
    ],
    "innovation": [
        "innovation",
        "futuretech",
        "future tech",
        "breakthrough",
        "invention",
        "new technology",
        "advanced",
        "next-generation",
        "futuristic",
        "smart",
        "automation",
        "load-bearing",
        "solid-state",
        "next-gen",
    ],
    "women": ["women", "woman", "girls", "female", "beauty", "fashion", "makeup", "skincare"],
    "relationships": ["relationship", "dating", "marriage", "breakup", "partner", "love", "red flag"],
    "psychology": ["psychology", "habit", "mental", "emotion", "confidence", "self-worth", "study says"],
    "lifestyle": ["lifestyle", "wellness", "fitness", "health", "travel", "home", "trend"],
    "culture": ["culture", "film", "music", "festival", "food", "sports", "creator"],
}

TRIGGER_KEYWORDS = {
    "ambition": ["growth", "hiring", "funding", "wealth", "founder", "success", "career", "skill", "global"],
    "fear": ["layoff", "replace", "risk", "threat", "crisis", "automation", "job", "collapse", "fall", "decline", "warns"],
    "curiosity": [
        "study",
        "reveals",
        "quietly",
        "secret",
        "hidden",
        "new",
        "why",
        "how",
        "works",
        "mechanism",
        "physics",
        "most people",
        "no idea",
        "never realize",
        "trend",
    ],
    "nationalism": ["india", "indian", "bharat", "rupee", "defense", "manufacturing"],
    "pride": ["wins", "record", "largest", "first", "global", "growth", "milestone"],
    "urgency": ["breaking", "urgent", "deadline", "race", "war", "crisis", "ban", "new rules", "warns", "dramatic"],
    "relatability": ["women", "girls", "relationship", "habit", "career", "dating", "workplace"],
    "emotion": ["love", "breakup", "lonely", "confidence", "fear", "pressure", "self-worth"],
    "self-worth": ["confidence", "boundaries", "career", "self-worth", "respect", "standards"],
}

HIGH_IMPACT_TERMS = {
    "ipo": 1.4,
    "trillionaire": 1.4,
    "billionaire": 0.9,
    "elon musk": 1.0,
    "spacex": 1.0,
    "google": 0.8,
    "openai": 0.9,
    "ai industry": 1.0,
    "smart glasses": 0.8,
    "record annual loss": 0.8,
    "restructuring": 0.7,
    "trade deal": 0.8,
    "child safety": 0.7,
    "roblox": 0.7,
    "startup grant": 0.6,
    "union recognition": 0.6,
    "engineering hubs": 0.6,
    "how it works": 0.8,
    "looks impossible": 1.0,
    "pure physics": 0.9,
    "simple trick": 0.8,
    "this tool": 0.7,
    "this system": 0.7,
    "in seconds": 0.6,
    "without digging": 0.8,
    "engineering": 0.7,
    "innovation": 0.7,
    "robotics": 0.8,
    "futuretech": 0.8,
    "construction": 0.5,
    "automotive": 0.5,
    "origami": 0.7,
    "load-bearing": 0.7,
    "solid-state": 0.6,
    "solar cells": 0.5,
    "3d printing": 0.7,
}

LOW_IMPACT_TERMS = {
    "worm-eating": 1.8,
    "snake": 1.5,
    "herpetologist": 1.4,
    "specimens": 1.0,
    "hockey coach": 1.2,
    "padma shri": 0.8,
    "honoured": 0.7,
}

LOCAL_GOVERNMENT_TERMS = [
    "cabinet approves",
    "state cabinet",
    "assembly",
    "minister",
    "government",
    "bihar",
    "karnataka",
    "west bengal",
    "mizoram",
]

RISK_KEYWORDS = {
    "high": [
        "terror",
        "communal",
        "religion",
        "riot",
        "suicide",
        "rape",
        "murder",
        "minor",
        "medical cure",
        "hate",
        "traitor",
        "traitors",
        "attacking the constitution",
    ],
    "medium": [
        "war",
        "border",
        "election",
        "politics",
        "layoff",
        "lawsuit",
        "crime",
        "sanction",
        "ban",
        "replace jobs",
    ],
}


def _combined_text(raw_item: dict[str, Any]) -> str:
    return " ".join(
        str(raw_item.get(key, "") or "")
        for key in ("title", "summary", "niche_hint")
    ).lower()


def _content_text(raw_item: dict[str, Any]) -> str:
    return " ".join(
        str(raw_item.get(key, "") or "")
        for key in ("title", "summary")
    ).lower()


def _hint_text(raw_item: dict[str, Any]) -> str:
    return str(raw_item.get("niche_hint", "") or "").lower()


def _contains_keyword(text: str, keyword: str) -> bool:
    if " " not in keyword and keyword.replace("-", "").isalpha():
        return re.search(rf"\b{re.escape(keyword)}\b", text) is not None
    return keyword in text


def _keyword_hits(text: str, keywords: list[str]) -> int:
    return sum(1 for keyword in keywords if _contains_keyword(text, keyword))


def infer_categories(text: str) -> list[str]:
    categories = [
        category
        for category, keywords in CATEGORY_KEYWORDS.items()
        if _keyword_hits(text, keywords)
    ]
    if "domestic_politics" in categories and "India" not in categories:
        categories.append("India")
    return categories or ["general"]


def infer_categories_with_hints(text: str, hint: str) -> list[str]:
    categories = infer_categories(text)
    if categories != ["general"] or not hint:
        return categories
    hinted = [category for category in infer_categories(hint) if category != "India"]
    return hinted or categories


def infer_country_relevance(text: str, categories: list[str]) -> str:
    if "India" in categories:
        return "India"
    if any(token in text for token in ["us ", "usa", "america", "silicon valley", "white house"]):
        return "United States"
    if any(token in text for token in ["china", "russia", "europe", "global", "world"]):
        return "Global"
    return "Global"


def infer_emotional_triggers(text: str, categories: list[str], country_relevance: str) -> list[str]:
    triggers = [
        trigger
        for trigger, keywords in TRIGGER_KEYWORDS.items()
        if _keyword_hits(text, keywords)
    ]
    if "AI" in categories and "curiosity" not in triggers:
        triggers.append("curiosity")
    if categories and set(categories).intersection({"engineering", "visual_explainer", "innovation"}) and "curiosity" not in triggers:
        triggers.append("curiosity")
    if "jobs" in categories and "fear" not in triggers:
        triggers.append("fear")
    if country_relevance == "India" and "pride" not in triggers:
        triggers.append("pride")
    if "domestic_politics" in categories and "urgency" not in triggers:
        triggers.append("urgency")
    return triggers or ["curiosity"]


def infer_risk_level(text: str, categories: list[str]) -> str:
    if "domestic_politics" in categories:
        return "high"
    if _keyword_hits(text, RISK_KEYWORDS["high"]):
        return "high"
    if _keyword_hits(text, RISK_KEYWORDS["medium"]) or "geopolitics" in categories:
        return "medium"
    return "low"


def score_virality(
    text: str,
    categories: list[str],
    emotional_triggers: list[str],
    risk_level: str,
) -> float:
    score = 4.0
    category_boosts = {
        "AI": 1.4,
        "business": 0.9,
        "jobs": 1.1,
        "India": 1.0,
        "domestic_politics": 0.7,
        "geopolitics": 0.8,
        "engineering": 1.1,
        "visual_explainer": 1.2,
        "innovation": 1.0,
        "women": 0.8,
        "relationships": 1.0,
        "psychology": 0.7,
        "infrastructure": 0.5,
    }
    for category in categories:
        score += category_boosts.get(category, 0.2)

    score += min(len(emotional_triggers) * 0.35, 1.4)
    if re.search(r"\b(first|largest|record|billion|million|quietly|secret|ban|race|impossible|hidden|simple|seconds)\b", text):
        score += 0.8
    for term, boost in HIGH_IMPACT_TERMS.items():
        if term in text:
            score += boost
    for term, penalty in LOW_IMPACT_TERMS.items():
        if term in text:
            score -= penalty
    if any(term in text for term in LOCAL_GOVERNMENT_TERMS) and not any(
        term in text for term in ["startup", "ai", "ipo", "trade deal", "global", "billion", "record"]
    ):
        score -= 0.7
    if re.search(r"\d", text):
        score += 0.3
    if risk_level == "medium":
        score += 0.2
    if risk_level == "high":
        score -= 1.0
    return round(max(1.0, min(score, 10.0)), 1)


def classify_topic(raw_item: dict[str, Any]) -> dict[str, Any]:
    text = _content_text(raw_item)
    hint = _hint_text(raw_item)
    scored_text = " ".join(part for part in (text, hint) if part)
    categories = infer_categories_with_hints(text, hint)
    country_relevance = infer_country_relevance(text, categories)
    emotional_triggers = infer_emotional_triggers(scored_text, categories, country_relevance)
    risk_level = infer_risk_level(text, categories)
    return {
        "categories": categories,
        "country_relevance": country_relevance,
        "emotional_triggers": emotional_triggers,
        "page_suitability": {},
        "virality_score": score_virality(scored_text, categories, emotional_triggers, risk_level),
        "risk_level": risk_level,
    }
