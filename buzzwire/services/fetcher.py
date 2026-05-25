from __future__ import annotations

from typing import Any
from urllib.request import Request, urlopen

from buzzwire.services.text_utils import clean_text


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
    for entry in feed.entries[:limit]:
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
    return items
