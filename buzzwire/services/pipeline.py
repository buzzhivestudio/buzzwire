from __future__ import annotations

import time
from typing import Any

from buzzwire import storage
from buzzwire.services.classifier import classify_topic
from buzzwire.services.fetcher import fetch_rss_source
from buzzwire.services.llm import get_provider
from buzzwire.services.matcher import match_pages


def _variant_seed(raw_item_id: int, raw_item: dict[str, Any], profile: dict[str, Any], variant_hint: int) -> int:
    fingerprint = f"{raw_item_id}:{profile.get('id', '')}:{raw_item.get('title', '')}"
    stable = sum((index + 1) * ord(char) for index, char in enumerate(fingerprint))
    return variant_hint + stable


def process_raw_item(
    conn: Any,
    raw_item_id: int,
    *,
    variant_hint: int = 0,
    tone_override: str | None = None,
) -> dict[str, Any]:
    raw_item = storage.get_raw_item(conn, raw_item_id)
    profiles = storage.get_profiles(conn)
    classification = classify_topic(raw_item)
    matches, suitability = match_pages(profiles, classification, raw_item)
    classification["page_suitability"] = suitability
    classification_id = storage.save_classification(conn, raw_item_id, classification)

    provider = get_provider()
    generated_ids = []
    for profile in matches:
        payload = provider.generate_post(
            raw_item,
            classification,
            profile,
            variant_hint=_variant_seed(raw_item_id, raw_item, profile, variant_hint),
            tone_override=tone_override,
        )
        post_id = storage.save_generated_post(
            conn,
            raw_item_id=raw_item_id,
            classified_topic_id=classification_id,
            page_profile_id=profile["id"],
            payload=payload,
        )
        generated_ids.append(post_id)

    return {
        "raw_item_id": raw_item_id,
        "classification_id": classification_id,
        "matches": [profile["page_name"] for profile in matches],
        "generated_post_ids": generated_ids,
    }


def process_manual_topic(
    conn: Any,
    *,
    title: str,
    summary: str = "",
    source_url: str = "",
    niche_hint: str = "",
) -> dict[str, Any]:
    raw_item_id = storage.insert_raw_item(
        conn,
        source_id=None,
        input_type="manual",
        title=title,
        summary=summary,
        url=source_url or None,
        niche_hint=niche_hint,
    )
    return process_raw_item(conn, raw_item_id, variant_hint=int(time.time()))


def fetch_and_process_rss(conn: Any, limit_per_source: int = 4) -> dict[str, Any]:
    sources = storage.get_sources(conn, enabled_only=True)
    fetched = 0
    processed = []
    errors = []
    for source in sources:
        try:
            items = fetch_rss_source(source, limit=limit_per_source)
        except Exception as exc:
            errors.append({"source": source["name"], "error": str(exc)})
            continue

        for item in items:
            raw_item_id = storage.insert_raw_item(conn, **item)
            fetched += 1
            processed.append(process_raw_item(conn, raw_item_id, variant_hint=int(time.time())))

    return {
        "sources_checked": len(sources),
        "items_fetched": fetched,
        "items_processed": len(processed),
        "processed": processed,
        "errors": errors,
    }


def regenerate_post(
    conn: Any,
    post_id: int,
    *,
    mode: str,
    tone_override: str | None = None,
) -> dict[str, Any]:
    detail = storage.get_generated_post_detail(conn, post_id)
    raw_item = {
        "id": detail["raw_item_id"],
        "title": detail["topic_title"],
        "summary": detail["topic_summary"],
        "url": detail["topic_url"],
        "niche_hint": detail["niche_hint"],
    }
    classification = {
        "categories": detail["categories"],
        "country_relevance": detail["country_relevance"],
        "emotional_triggers": detail["emotional_triggers"],
        "page_suitability": detail["page_suitability"],
        "virality_score": detail["virality_score"],
        "risk_level": detail["risk_level"],
    }
    profile = {
        "id": detail["page_profile_id"],
        "page_name": detail["page_name"],
        "username": detail.get("username", ""),
        "niche": detail["niche"],
        "audience": detail["audience"],
        "emotional_drivers": detail["emotional_drivers"],
        "allowed_topics": detail["allowed_topics"],
        "blocked_topics": detail["blocked_topics"],
        "tone_rules": detail["tone_rules"],
        "headline_style": detail["headline_style"],
        "caption_style": detail["caption_style"],
        "visual_style": detail["visual_style"],
        "preferred_sources": detail.get("preferred_sources", []),
        "country_focus": detail.get("country_focus", ""),
        "risk_tolerance": detail["risk_tolerance"],
        "match_score": detail["page_suitability"].get(detail["page_name"], 4.0),
    }
    effective_tone = tone_override if tone_override is not None else detail.get("tone_override")
    payload = get_provider().generate_post(
        raw_item,
        classification,
        profile,
        variant_hint=int(time.time() + post_id),
        tone_override=effective_tone,
    )

    if mode == "title":
        fields = {
            "viral_title": payload["viral_title"],
            "aggressive_title": payload["aggressive_title"],
            "confidence_score": payload["confidence_score"],
        }
    elif mode == "caption":
        fields = {
            "caption": payload["caption"],
            "carousel_text": payload["carousel_text"],
            "confidence_score": payload["confidence_score"],
        }
    else:
        fields = dict(payload)
        fields["tone_override"] = effective_tone
    storage.update_generated_post_fields(conn, post_id, fields)
    return storage.get_generated_post_detail(conn, post_id)


def regenerate_ready_posts(conn: Any, *, limit: int = 100) -> dict[str, Any]:
    rows = conn.execute(
        """
        SELECT id
        FROM generated_posts
        WHERE status = 'generated'
        ORDER BY updated_at DESC, created_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    updated: list[int] = []
    errors: list[dict[str, Any]] = []
    for row in rows:
        post_id = int(row["id"])
        try:
            regenerate_post(conn, post_id, mode="all")
        except Exception as exc:
            errors.append({"post_id": post_id, "error": str(exc)[:180]})
            continue
        updated.append(post_id)
    return {"updated": len(updated), "post_ids": updated, "errors": errors}
