from __future__ import annotations

import html
import re


TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")
KNOWN_CASING = {
    "ai": "AI",
    "api": "API",
    "ceo": "CEO",
    "cfo": "CFO",
    "cto": "CTO",
    "fifa": "FIFA",
    "gta": "GTA",
    "gdp": "GDP",
    "imdb": "IMDb",
    "iphone": "iPhone",
    "it": "IT",
    "ishowspeed": "IShowSpeed",
    "mrbeast": "MrBeast",
    "openai": "OpenAI",
    "pewdiepie": "PewDiePie",
    "tiktok": "TikTok",
    "u.s": "U.S",
    "uk": "UK",
    "us": "US",
    "usa": "USA",
    "youtube": "YouTube",
}


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    without_tags = TAG_RE.sub(" ", value)
    return SPACE_RE.sub(" ", html.unescape(without_tags)).strip()


def contains_any(text: str, keywords: list[str]) -> bool:
    haystack = text.lower()
    return any(keyword.lower() in haystack for keyword in keywords)


def title_case_soft(value: str) -> str:
    words = []
    for word in clean_text(value).split():
        stripped = word.strip(".,:;!?()[]{}")
        prefix = word[: len(word) - len(word.lstrip(".,:;!?()[]{}"))]
        suffix = word[len(word.rstrip(".,:;!?()[]{}")) :]
        known = KNOWN_CASING.get(stripped.lower())
        if known:
            words.append(f"{prefix}{known}{suffix}")
        elif word.isupper() and len(word) <= 5:
            words.append(word)
        else:
            words.append(word[:1].upper() + word[1:].lower())
    return " ".join(words)


def first_sentence(value: str, fallback: str = "") -> str:
    text = clean_text(value)
    if not text:
        return fallback
    match = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)
    return match[0].strip()
