from __future__ import annotations

import re
from typing import Any


RISK_ORDER = {"low": 1, "medium": 2, "high": 3}

BUSINESS_PAGE_NAMES = {"SuccessAddictives", "CEOBeingCEO"}
BUSINESS_CATEGORIES = {"ai", "business", "jobs"}
BUSINESS_TEXT_TERMS = {
    "ai",
    "startup",
    "funding",
    "ipo",
    "market",
    "stock",
    "revenue",
    "profit",
    "ceo",
    "founder",
    "hiring",
    "union",
    "restructuring",
    "trade deal",
    "investment",
    "productivity",
    "workforce",
    "boss",
    "entry-level",
    "entry level",
    "company",
}

SUCCESS_EXPLAINER_CATEGORIES = {"engineering", "visual_explainer", "innovation", "infrastructure"}
SUCCESS_EXPLAINER_TERMS = {
    "how it works",
    "why it works",
    "looks impossible",
    "most people",
    "no idea",
    "hidden",
    "mechanism",
    "mechanical",
    "physics",
    "engineered",
    "engineering",
    "tool",
    "wrench",
    "construction",
    "repair",
    "sealant",
    "pipe",
    "plumbing",
    "prototype",
    "robotics",
    "drone",
    "scanner",
    "sensor",
    "motor",
    "battery",
    "vehicle",
    "automotive",
    "in seconds",
    "without digging",
}

SUCCESS_WEALTH_CATEGORIES = {
    "engineering",
    "visual_explainer",
    "innovation",
    "infrastructure",
    "geopolitics",
    "culture",
    "entertainment",
    "influencers",
    "sports",
    "history",
    "places",
    "money",
}
SUCCESS_WEALTH_TERMS = {
    "world cup",
    "olympics",
    "movie",
    "movies",
    "hollywood",
    "celebrity",
    "box office",
    "film",
    "series",
    "episode",
    "finale",
    "cast",
    "netflix",
    "spotify",
    "album",
    "song",
    "drake",
    "michael jackson",
    "shakira",
    "rihanna",
    "taylor swift",
    "beyonce",
    "emmy",
    "oscar",
    "pewdiepie",
    "mrbeast",
    "marzia",
    "youtube",
    "youtuber",
    "streamer",
    "influencer",
    "creator economy",
    "family vlogs",
    "followers",
    "subscribers",
    "privacy",
    "ronaldo",
    "messi",
    "gta",
    "playstation",
    "iphone",
    "ferrari",
    "tesla",
    "trump",
    "xi jinping",
    "iran",
    "china",
    "debt",
    "richest",
    "trillion",
    "billion",
    "profit",
    "bank",
    "banks",
    "empire",
    "empires",
    "presidents",
    "countries",
    "cities",
    "places",
    "buildings",
    "homes",
    "mansion",
    "airport",
    "road",
    "earth",
    "first time",
    "first ever",
    "highest in history",
    "biggest",
    "longest",
    "most powerful",
    "insane",
    "before and after",
    "digital detox",
    "gen z",
    "human-interest",
    "wholesome",
}

JOB_MARKET_TERMS = {
    "entry-level job",
    "entry level job",
    "graduate job",
    "fall in jobs",
    "job market",
    "job losses",
    "jobs decline",
    "dramatic fall",
    "hiring slowdown",
    "layoff",
    "layoffs",
    "workforce",
    "white collar",
    "automation",
}

LOCAL_GOVERNMENT_TERMS = {
    "cabinet",
    "assembly",
    "minister",
    "government",
    "state government",
    "bihar",
    "karnataka",
    "west bengal",
    "mizoram",
}

GLOBAL_INDIA_ALLOWED_TERMS = {
    "trade deal",
    "china",
    "gulf",
    "sanction",
    "war",
    "defense",
    "border",
    "supply chain",
}

HIGH_IMPACT_BUSINESS_TERMS = {
    "ipo",
    "trillionaire",
    "billionaire",
    "ai",
    "startup",
    "restructuring",
    "record annual loss",
    "smart glasses",
    "trade deal",
    "union recognition",
    "child safety",
    "roblox",
    "spacex",
    "google",
    "ubisoft",
}


def _words(value: str) -> set[str]:
    return {word.lower() for word in re.findall(r"[a-zA-Z][a-zA-Z-]+", value)}


def _text_blob(raw_item: dict[str, Any], classification: dict[str, Any]) -> str:
    return " ".join(
        [
            str(raw_item.get("title", "")),
            str(raw_item.get("summary", "")),
            str(raw_item.get("niche_hint", "")),
            " ".join(classification.get("categories", [])),
            classification.get("country_relevance", ""),
        ]
    ).lower()


def _contains_term(text: str, term: str) -> bool:
    normalized = term.lower().strip()
    if not normalized:
        return False
    if " " not in normalized and normalized.replace("-", "").isalnum():
        return re.search(rf"\b{re.escape(normalized)}\b", text) is not None
    return normalized in text


def _term_match_score(terms: list[str], text: str, categories: set[str]) -> float:
    score = 0.0
    for term in terms:
        normalized = term.lower()
        if _contains_term(text, normalized):
            score += 1.4
        elif normalized in categories:
            score += 1.2
        else:
            term_words = _words(normalized)
            if term_words and term_words.intersection(categories):
                score += 0.7
    return score


def score_profile(
    profile: dict[str, Any],
    classification: dict[str, Any],
    raw_item: dict[str, Any],
) -> float:
    text = _text_blob(raw_item, classification)
    categories = {category.lower() for category in classification.get("categories", [])}
    page_name = profile.get("page_name", "")
    blocked_topics = profile.get("blocked_topics", [])
    if any(blocked.lower() in text for blocked in blocked_topics):
        return 0.0

    if "domestic_politics" in categories and page_name != "IndiaPulse":
        return 0.0

    virality = float(classification.get("virality_score", 1))
    clear_business_signal = bool(categories.intersection(BUSINESS_CATEGORIES)) or any(
        _contains_term(text, term) for term in BUSINESS_TEXT_TERMS
    )
    explainer_signal = bool(categories.intersection(SUCCESS_EXPLAINER_CATEGORIES)) or any(
        _contains_term(text, term) for term in SUCCESS_EXPLAINER_TERMS
    )
    wealth_signal = bool(categories.intersection(SUCCESS_WEALTH_CATEGORIES)) or any(
        _contains_term(text, term) for term in SUCCESS_WEALTH_TERMS
    )
    job_market_signal = "jobs" in categories and any(
        _contains_term(text, term) for term in JOB_MARKET_TERMS
    )
    if virality < 5.7 and "domestic_politics" not in categories:
        lower_floor_business_story = (
            page_name in BUSINESS_PAGE_NAMES
            and virality >= 5.0
            and (clear_business_signal or job_market_signal)
        )
        lower_floor_success_explainer = (
            page_name == "SuccessAddictives"
            and virality >= 5.0
            and (explainer_signal or wealth_signal)
        )
        if not (lower_floor_business_story or lower_floor_success_explainer):
            return 0.0

    if page_name in BUSINESS_PAGE_NAMES:
        if page_name == "SuccessAddictives":
            if not (clear_business_signal or explainer_signal or wealth_signal):
                return 0.0
        elif not clear_business_signal:
            return 0.0
        local_government_story = any(_contains_term(text, term) for term in LOCAL_GOVERNMENT_TERMS)
        high_impact_business = any(_contains_term(text, term) for term in HIGH_IMPACT_BUSINESS_TERMS)
        if local_government_story and not high_impact_business:
            return 0.0

    if page_name == "IndiaPulse" and classification.get("country_relevance") != "India":
        global_india_signal = "geopolitics" in categories and any(
            _contains_term(text, term) for term in GLOBAL_INDIA_ALLOWED_TERMS
        )
        if not global_india_signal:
            return 0.0

    if page_name == "HerSignal":
        female_signal = categories.intersection({"women", "relationships", "psychology", "lifestyle", "jobs", "business"})
        policy_or_infra = categories.intersection({"infrastructure", "domestic_politics", "geopolitics"})
        if policy_or_infra and not categories.intersection({"women", "relationships", "psychology"}):
            return 0.0
        if classification.get("country_relevance") == "India" and not categories.intersection({"women", "relationships"}):
            return 0.0
        if not female_signal:
            return 0.0

    risk_level = classification.get("risk_level", "low")
    risk_tolerance = profile.get("risk_tolerance", "medium")
    politics_allowed_for_india = "domestic_politics" in categories and page_name == "IndiaPulse"
    if not politics_allowed_for_india and RISK_ORDER.get(risk_level, 1) > RISK_ORDER.get(risk_tolerance, 2):
        return 0.0

    allowed_topics = profile.get("allowed_topics", [])
    niche_terms = [part.strip() for part in profile.get("niche", "").split(",") if part.strip()]
    score = 0.0
    score += _term_match_score(allowed_topics, text, categories)
    score += _term_match_score(niche_terms, text, categories) * 0.9

    driver_overlap = set(profile.get("emotional_drivers", [])).intersection(
        classification.get("emotional_triggers", [])
    )
    score += len(driver_overlap) * 1.3

    if classification.get("country_relevance") == "India" and "india" in profile.get("niche", "").lower():
        score += 2.0
    if "women" in categories and "women" in profile.get("niche", "").lower():
        score += 1.7
    if "AI" in classification.get("categories", []) and "ai" in profile.get("niche", "").lower():
        score += 1.7
    if politics_allowed_for_india:
        score += 2.6
    if any(_contains_term(text, term) for term in HIGH_IMPACT_BUSINESS_TERMS):
        score += 1.4
    if page_name in BUSINESS_PAGE_NAMES and job_market_signal:
        score += 1.4
    if page_name == "SuccessAddictives" and explainer_signal:
        score += 3.0
    if page_name == "SuccessAddictives" and wealth_signal:
        score += 2.6
    if page_name == "CEOBeingCEO" and any(
        _contains_term(text, term)
        for term in {"ipo", "trillionaire", "ai", "restructuring", "trade deal", "union recognition", "roblox"}
    ):
        score += 0.8
    if page_name == "CEOBeingCEO" and job_market_signal and any(
        _contains_term(text, term) for term in {"boss", "ceo", "executive", "leader", "manager"}
    ):
        score += 1.0

    score += virality / 5.0
    if risk_level == "medium" and risk_tolerance == "medium":
        score -= 0.2
    return round(score, 2)


def match_pages(
    profiles: list[dict[str, Any]],
    classification: dict[str, Any],
    raw_item: dict[str, Any],
    threshold: float = 5.0,
) -> tuple[list[dict[str, Any]], dict[str, float]]:
    scored = []
    suitability = {}
    for profile in profiles:
        score = score_profile(profile, classification, raw_item)
        suitability[profile["page_name"]] = score
        if score >= threshold:
            enriched = dict(profile)
            enriched["match_score"] = score
            scored.append(enriched)
    scored.sort(key=lambda item: item["match_score"], reverse=True)
    return scored, suitability
