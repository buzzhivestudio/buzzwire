from __future__ import annotations

import re
from typing import Any
from urllib.request import Request, urlopen

from buzzwire.services.text_utils import clean_text


WEALTH_SIGNAL_TERMS = {
    "after",
    "before and after",
    "biggest",
    "billion",
    "billionaire",
    "built",
    "cast",
    "ceo",
    "celebrity",
    "china",
    "cities",
    "city",
    "countries",
    "creator",
    "creator economy",
    "debt",
    "drake",
    "emmy",
    "episode",
    "ever",
    "ferrari",
    "fifa",
    "finale",
    "first ever",
    "for the first time",
    "gta",
    "highest",
    "highest in history",
    "hollywood",
    "history",
    "influencer",
    "instagram",
    "iphone",
    "ishowspeed",
    "japan",
    "kai cenat",
    "ksi",
    "longest",
    "marzia",
    "mansion",
    "million",
    "mrbeast",
    "most",
    "movie",
    "movie lineup",
    "movies",
    "netflix",
    "olympics",
    "oscar",
    "playstation",
    "pewdiepie",
    "profit",
    "privacy",
    "record",
    "richest",
    "ronaldo",
    "series",
    "streamer",
    "subscribers",
    "spotify",
    "tiktok",
    "tiktoker",
    "trillion",
    "trillionaire",
    "world cup",
    "youtube",
    "youtuber",
}

VISUAL_SIGNAL_TERMS = {
    "airport",
    "animal",
    "animals",
    "apocalypse",
    "building",
    "buildings",
    "car",
    "cars",
    "design",
    "earth",
    "flying",
    "future",
    "gen z",
    "homes",
    "how it works",
    "human interest",
    "insane",
    "look like",
    "places",
    "road",
    "robot",
    "space",
    "stole",
    "viral",
    "wholesome",
    "weird",
}

WEAK_NEWS_TERMS = {
    "appoints",
    "court says",
    "hearing",
    "meeting",
    "minister says",
    "panel",
    "press conference",
    "shares fall",
    "statement",
    "stock slips",
    "told reporters",
}

GOSSIP_ONLY_TERMS = {
    "breakup",
    "cheating",
    "dating",
    "divorce",
    "feud",
    "girlfriend",
    "rumor",
    "split",
}

ROUTINE_POLITICS_TERMS = {
    "assembly",
    "bjp",
    "congress",
    "election",
    "minister",
    "parliament",
    "party workers",
    "rahul",
}


def _contains_term(text: str, term: str) -> bool:
    if " " not in term and term.replace("-", "").isalnum():
        return re.search(rf"\b{re.escape(term)}\b", text) is not None
    return term in text


def score_rss_item_for_success(raw_item: dict[str, Any], source: dict[str, Any]) -> float:
    """Score items before classification so feeds surface visual, viral stories first."""
    title = str(raw_item.get("title", "") or "")
    summary = str(raw_item.get("summary", "") or "")
    niche = str(source.get("niche", "") or raw_item.get("niche_hint", "") or "")
    text = " ".join([title, summary, niche]).lower()
    source_niche = niche.lower()
    score = 0.0

    if re.search(r"(\$|#|\b\d+(?:\.\d+)?\s*(?:k|m|b|million|billion|trillion|%)?\b)", text):
        score += 2.4
    if re.search(r"\b(most|biggest|richest|highest|longest|best|top\s+\d+|#\d+)\b", text):
        score += 2.1
    if re.search(r"\b(first ever|first-ever|for the first time|first time|highest in history|record|after\s+\d+\s+years)\b", text):
        score += 2.2

    score += sum(0.55 for term in WEALTH_SIGNAL_TERMS if _contains_term(text, term))
    score += sum(0.45 for term in VISUAL_SIGNAL_TERMS if _contains_term(text, term))
    score -= sum(0.65 for term in WEAK_NEWS_TERMS if _contains_term(text, term))
    if any(_contains_term(text, term) for term in GOSSIP_ONLY_TERMS) and not any(
        _contains_term(text, term)
        for term in {
            "career",
            "business",
            "privacy",
            "children",
            "family",
            "net worth",
            "million",
            "billion",
            "record",
            "launch",
            "album",
            "movie",
        }
    ):
        score -= 2.0

    if any(term in source_niche for term in ("viral knowledge", "entertainment", "sports", "history", "places", "money")):
        score += 1.2
    if any(term in source_niche for term in ("hollywood", "celebr", "influencer", "youtuber", "streamer", "creator", "pubity-style", "human-interest", "gen z", "internet culture")):
        score += 1.6
    if any(term in source_niche for term in ("visual explainer", "engineering", "innovation", "future tech", "science")):
        score += 0.9
    if "india, national" in source_niche and any(_contains_term(text, term) for term in ROUTINE_POLITICS_TERMS):
        score -= 2.2

    title_words = len(re.findall(r"[A-Za-z0-9$#]+", title))
    if 5 <= title_words <= 18:
        score += 0.7
    elif title_words > 24:
        score -= 0.5

    return round(score, 2)


def rank_rss_items_for_success(
    items: list[dict[str, Any]],
    source: dict[str, Any],
    limit: int,
) -> list[dict[str, Any]]:
    ranked = [
        (score_rss_item_for_success(item, source), index, item)
        for index, item in enumerate(items)
    ]
    ranked.sort(key=lambda row: (-row[0], row[1]))
    return [item for _, _, item in ranked[:limit]]


def fetch_rss_source(source: dict[str, Any], limit: int = 5) -> list[dict[str, Any]]:
    try:
        import feedparser
    except ModuleNotFoundError as exc:
        raise RuntimeError("Missing RSS parser library. Run: pip install -r requirements.txt") from exc

    request = Request(
        source["url"],
        headers={"User-Agent": "BuzzWireMVP/0.1 (+local approval dashboard)"},
    )
    with urlopen(request, timeout=15) as response:
        data = response.read(2_500_000)

    feed = feedparser.parse(data)
    items: list[dict[str, Any]] = []
    scan_limit = max(limit * 8, 32)
    for entry in feed.entries[:scan_limit]:
        title = clean_text(entry.get("title", ""))
        if not title:
            continue
        items.append(
            {
                "source_id": source["id"],
                "input_type": "rss",
                "title": title,
                "summary": clean_text(entry.get("summary", entry.get("description", ""))),
                "url": entry.get("link"),
                "published_at": entry.get("published", entry.get("updated")),
                "niche_hint": source.get("niche", ""),
            }
        )
    return rank_rss_items_for_success(items, source, limit)
