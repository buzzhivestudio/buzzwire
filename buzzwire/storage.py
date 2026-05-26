from __future__ import annotations

import json
from typing import Any

from buzzwire.db import DatabaseIntegrityError


JSON_FIELDS = {
    "emotional_drivers",
    "allowed_topics",
    "blocked_topics",
    "preferred_sources",
    "categories",
    "emotional_triggers",
    "page_suitability",
    "carousel_text",
    "suggested_image_keywords",
    "image_brief",
}


def dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True)


def loads(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def row_to_dict(row: Any | None) -> dict[str, Any] | None:
    if row is None:
        return None
    output = dict(row)
    for field in JSON_FIELDS:
        if field in output:
            fallback = {} if field in {"page_suitability", "image_brief"} else []
            output[field] = loads(output[field], fallback)
    return output


def rows_to_dicts(rows: list[Any]) -> list[dict[str, Any]]:
    return [row_to_dict(row) for row in rows if row is not None]


def get_profiles(conn: Any) -> list[dict[str, Any]]:
    rows = conn.execute("SELECT * FROM page_profiles ORDER BY page_name").fetchall()
    return rows_to_dicts(rows)


def upsert_profile(conn: Any, payload: dict[str, Any], profile_id: int | None = None) -> dict[str, Any]:
    values = {
        "page_name": str(payload["page_name"]).strip(),
        "username": str(payload.get("username", "")).strip(),
        "niche": str(payload.get("niche", "")).strip(),
        "audience": str(payload.get("audience", "")).strip(),
        "emotional_drivers": payload.get("emotional_drivers", []),
        "allowed_topics": payload.get("allowed_topics", []),
        "blocked_topics": payload.get("blocked_topics", []),
        "tone_rules": str(payload.get("tone_rules", "")).strip(),
        "headline_style": str(payload.get("headline_style", "")).strip(),
        "caption_style": str(payload.get("caption_style", "")).strip(),
        "visual_style": str(payload.get("visual_style", "")).strip(),
        "preferred_sources": payload.get("preferred_sources", []),
        "country_focus": str(payload.get("country_focus", "")).strip(),
        "risk_tolerance": str(payload.get("risk_tolerance", "medium")).strip() or "medium",
    }
    if profile_id is None:
        cur = conn.execute(
            """
            INSERT INTO page_profiles (
                page_name, username, niche, audience, emotional_drivers, allowed_topics,
                blocked_topics, tone_rules, headline_style, caption_style,
                visual_style, preferred_sources, country_focus, risk_tolerance
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(page_name) DO UPDATE SET
                username = excluded.username,
                niche = excluded.niche,
                audience = excluded.audience,
                emotional_drivers = excluded.emotional_drivers,
                allowed_topics = excluded.allowed_topics,
                blocked_topics = excluded.blocked_topics,
                tone_rules = excluded.tone_rules,
                headline_style = excluded.headline_style,
                caption_style = excluded.caption_style,
                visual_style = excluded.visual_style,
                preferred_sources = excluded.preferred_sources,
                country_focus = excluded.country_focus,
                risk_tolerance = excluded.risk_tolerance,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                values["page_name"],
                values["username"],
                values["niche"],
                values["audience"],
                dumps(values["emotional_drivers"]),
                dumps(values["allowed_topics"]),
                dumps(values["blocked_topics"]),
                values["tone_rules"],
                values["headline_style"],
                values["caption_style"],
                values["visual_style"],
                dumps(values["preferred_sources"]),
                values["country_focus"],
                values["risk_tolerance"],
            ),
        )
        row_id = int(conn.execute(
            "SELECT id FROM page_profiles WHERE page_name = ?",
            (values["page_name"],),
        ).fetchone()["id"])
    else:
        conn.execute(
            """
            UPDATE page_profiles SET
                page_name = ?,
                username = ?,
                niche = ?,
                audience = ?,
                emotional_drivers = ?,
                allowed_topics = ?,
                blocked_topics = ?,
                tone_rules = ?,
                headline_style = ?,
                caption_style = ?,
                visual_style = ?,
                preferred_sources = ?,
                country_focus = ?,
                risk_tolerance = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                values["page_name"],
                values["username"],
                values["niche"],
                values["audience"],
                dumps(values["emotional_drivers"]),
                dumps(values["allowed_topics"]),
                dumps(values["blocked_topics"]),
                values["tone_rules"],
                values["headline_style"],
                values["caption_style"],
                values["visual_style"],
                dumps(values["preferred_sources"]),
                values["country_focus"],
                values["risk_tolerance"],
                profile_id,
            ),
        )
        row_id = profile_id
    conn.commit()
    row = conn.execute("SELECT * FROM page_profiles WHERE id = ?", (row_id,)).fetchone()
    profile = row_to_dict(row)
    if profile is None:
        raise ValueError(f"Page profile {row_id} not found")
    return profile


def get_sources(conn: Any, enabled_only: bool = False) -> list[dict[str, Any]]:
    if enabled_only:
        rows = conn.execute("SELECT * FROM sources WHERE enabled = 1 ORDER BY name").fetchall()
    else:
        rows = conn.execute("SELECT * FROM sources ORDER BY name").fetchall()
    return rows_to_dicts(rows)


def insert_raw_item(
    conn: Any,
    *,
    source_id: int | None,
    input_type: str,
    title: str,
    summary: str = "",
    url: str | None = None,
    published_at: str | None = None,
    niche_hint: str = "",
) -> int:
    clean_url = url.strip() if url else None
    try:
        cur = conn.execute(
            """
            INSERT INTO raw_items (
                source_id, input_type, title, summary, url, published_at, niche_hint
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            RETURNING id
            """,
            (source_id, input_type, title.strip(), summary.strip(), clean_url, published_at, niche_hint.strip()),
        )
        row = cur.fetchone()
        conn.commit()
        return int(row["id"])
    except DatabaseIntegrityError:
        conn.rollback()
        if not clean_url:
            raise
        row = conn.execute("SELECT id FROM raw_items WHERE url = ?", (clean_url,)).fetchone()
        return int(row["id"])


def get_raw_item(conn: Any, raw_item_id: int) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM raw_items WHERE id = ?", (raw_item_id,)).fetchone()
    item = row_to_dict(row)
    if item is None:
        raise ValueError(f"Raw item {raw_item_id} not found")
    return item


def save_classification(
    conn: Any,
    raw_item_id: int,
    classification: dict[str, Any],
) -> int:
    cur = conn.execute(
        """
        INSERT INTO classified_topics (
            raw_item_id, categories, country_relevance, emotional_triggers,
            page_suitability, virality_score, risk_level
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(raw_item_id) DO UPDATE SET
            categories = excluded.categories,
            country_relevance = excluded.country_relevance,
            emotional_triggers = excluded.emotional_triggers,
            page_suitability = excluded.page_suitability,
            virality_score = excluded.virality_score,
            risk_level = excluded.risk_level
        RETURNING id
        """,
        (
            raw_item_id,
            dumps(classification["categories"]),
            classification["country_relevance"],
            dumps(classification["emotional_triggers"]),
            dumps(classification["page_suitability"]),
            classification["virality_score"],
            classification["risk_level"],
        ),
    )
    row = cur.fetchone()
    conn.commit()
    return int(row["id"])


def get_classification_for_raw(conn: Any, raw_item_id: int) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM classified_topics WHERE raw_item_id = ?",
        (raw_item_id,),
    ).fetchone()
    return row_to_dict(row)


def save_generated_post(
    conn: Any,
    *,
    raw_item_id: int,
    classified_topic_id: int,
    page_profile_id: int,
    payload: dict[str, Any],
) -> int:
    existing = conn.execute(
        """
        SELECT id, status FROM generated_posts
        WHERE raw_item_id = ? AND page_profile_id = ?
        """,
        (raw_item_id, page_profile_id),
    ).fetchone()
    if existing:
        if existing["status"] == "generated":
            conn.execute(
                """
                UPDATE generated_posts
                SET classified_topic_id = ?,
                    neutral_title = ?,
                    viral_title = ?,
                    aggressive_title = ?,
                    caption = ?,
                    carousel_text = ?,
                    visual_direction = ?,
                    suggested_image_keywords = ?,
                    image_brief = ?,
                    risk_notes = ?,
                    source_url = ?,
                    confidence_score = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    classified_topic_id,
                    payload["neutral_title"],
                    payload["viral_title"],
                    payload["aggressive_title"],
                    payload["caption"],
                    dumps(payload["carousel_text"]),
                    payload["visual_direction"],
                    dumps(payload["suggested_image_keywords"]),
                    dumps(payload.get("image_brief", {})),
                    payload["risk_notes"],
                    payload.get("source_url"),
                    payload["confidence_score"],
                    existing["id"],
                ),
            )
            conn.commit()
        return int(existing["id"])

    cur = conn.execute(
        """
        INSERT INTO generated_posts (
            raw_item_id, classified_topic_id, page_profile_id, neutral_title,
            viral_title, aggressive_title, caption, carousel_text,
            visual_direction, suggested_image_keywords, image_brief, risk_notes,
            source_url, confidence_score
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        RETURNING id
        """,
        (
            raw_item_id,
            classified_topic_id,
            page_profile_id,
            payload["neutral_title"],
            payload["viral_title"],
            payload["aggressive_title"],
            payload["caption"],
            dumps(payload["carousel_text"]),
            payload["visual_direction"],
            dumps(payload["suggested_image_keywords"]),
            dumps(payload.get("image_brief", {})),
            payload["risk_notes"],
            payload.get("source_url"),
            payload["confidence_score"],
        ),
    )
    row = cur.fetchone()
    conn.commit()
    return int(row["id"])


def get_generated_post_detail(conn: Any, post_id: int) -> dict[str, Any]:
    row = conn.execute(
        """
        SELECT
            gp.*,
            ri.title AS topic_title,
            ri.summary AS topic_summary,
            ri.url AS topic_url,
            ri.niche_hint,
            s.name AS source_name,
            s.url AS source_feed_url,
            ct.categories,
            ct.country_relevance,
            ct.emotional_triggers,
            ct.page_suitability,
            ct.virality_score,
            ct.risk_level,
            pp.page_name,
            pp.username,
            pp.niche,
            pp.audience,
            pp.emotional_drivers,
            pp.allowed_topics,
            pp.blocked_topics,
            pp.tone_rules,
            pp.headline_style,
            pp.caption_style,
            pp.visual_style,
            pp.preferred_sources,
            pp.country_focus,
            pp.risk_tolerance
        FROM generated_posts gp
        JOIN raw_items ri ON ri.id = gp.raw_item_id
        LEFT JOIN sources s ON s.id = ri.source_id
        JOIN classified_topics ct ON ct.id = gp.classified_topic_id
        JOIN page_profiles pp ON pp.id = gp.page_profile_id
        WHERE gp.id = ?
        """,
        (post_id,),
    ).fetchone()
    post = row_to_dict(row)
    if post is None:
        raise ValueError(f"Generated post {post_id} not found")
    return post


def update_generated_post_fields(conn: Any, post_id: int, fields: dict[str, Any]) -> None:
    allowed = {
        "neutral_title",
        "viral_title",
        "aggressive_title",
        "caption",
        "carousel_text",
        "visual_direction",
        "suggested_image_keywords",
        "image_brief",
        "risk_notes",
        "confidence_score",
        "status",
        "tone_override",
    }
    updates = []
    values: list[Any] = []
    for key, value in fields.items():
        if key not in allowed:
            continue
        updates.append(f"{key} = ?")
        if key in {"carousel_text", "suggested_image_keywords", "image_brief"}:
            values.append(dumps(value))
        else:
            values.append(value)
    if not updates:
        return
    updates.append("updated_at = CURRENT_TIMESTAMP")
    values.append(post_id)
    conn.execute(
        f"UPDATE generated_posts SET {', '.join(updates)} WHERE id = ?",
        values,
    )
    conn.commit()


def insert_approval(conn: Any, post_id: int, action: str, notes: str = "") -> None:
    conn.execute(
        "INSERT INTO approvals (generated_post_id, action, notes) VALUES (?, ?, ?)",
        (post_id, action, notes),
    )
    conn.commit()


def get_board(conn: Any) -> dict[str, list[dict[str, Any]]]:
    fetched = rows_to_dicts(
        conn.execute(
            """
            SELECT
                ri.*,
                s.name AS source_name,
                s.url AS source_feed_url
            FROM raw_items ri
            LEFT JOIN sources s ON s.id = ri.source_id
            LEFT JOIN classified_topics ct ON ct.raw_item_id = ri.id
            WHERE ct.id IS NULL
            ORDER BY ri.fetched_at DESC
            LIMIT 50
            """
        ).fetchall()
    )
    scored = rows_to_dicts(
        conn.execute(
            """
            SELECT
                ct.*,
                ri.title AS topic_title,
                ri.summary AS topic_summary,
                ri.url AS source_url,
                s.name AS source_name,
                s.url AS source_feed_url
            FROM classified_topics ct
            JOIN raw_items ri ON ri.id = ct.raw_item_id
            LEFT JOIN sources s ON s.id = ri.source_id
            LEFT JOIN generated_posts gp ON gp.classified_topic_id = ct.id
            WHERE gp.id IS NULL
            ORDER BY ct.created_at DESC
            LIMIT 50
            """
        ).fetchall()
    )
    posts = rows_to_dicts(
        conn.execute(
            """
            SELECT
                gp.*,
                pp.page_name,
                pp.username,
                ri.title AS topic_title,
                ri.summary AS topic_summary,
                ri.url AS topic_url,
                s.name AS source_name,
                s.url AS source_feed_url,
                ct.virality_score,
                ct.risk_level,
                ct.categories,
                ct.country_relevance,
                ct.emotional_triggers
            FROM generated_posts gp
            JOIN page_profiles pp ON pp.id = gp.page_profile_id
            JOIN raw_items ri ON ri.id = gp.raw_item_id
            LEFT JOIN sources s ON s.id = ri.source_id
            JOIN classified_topics ct ON ct.id = gp.classified_topic_id
            ORDER BY gp.updated_at DESC, gp.created_at DESC
            LIMIT 200
            """
        ).fetchall()
    )
    return {
        "fetched": fetched,
        "scored": scored,
        "generated": [post for post in posts if post["status"] == "generated"],
        "approved": [post for post in posts if post["status"] == "approved"],
        "rejected": [post for post in posts if post["status"] == "rejected"],
        "used": [post for post in posts if post["status"] == "used"],
    }


def get_approved_posts(conn: Any) -> list[dict[str, Any]]:
    return rows_to_dicts(
        conn.execute(
            """
            SELECT
                gp.*,
                pp.page_name,
                pp.username,
                ri.title AS topic_title,
                ct.virality_score,
                ct.risk_level
            FROM generated_posts gp
            JOIN page_profiles pp ON pp.id = gp.page_profile_id
            JOIN raw_items ri ON ri.id = gp.raw_item_id
            JOIN classified_topics ct ON ct.id = gp.classified_topic_id
            WHERE gp.status = 'approved'
            ORDER BY gp.updated_at DESC
            """
        ).fetchall()
    )
