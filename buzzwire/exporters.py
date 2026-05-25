from __future__ import annotations

import json
from typing import Any


def export_board_json(board: dict[str, Any]) -> str:
    return json.dumps(board, indent=2, ensure_ascii=True)


def export_approved_markdown(posts: list[dict[str, Any]]) -> str:
    if not posts:
        return "# BuzzWire Approved Posts\n\nNo approved posts yet.\n"

    lines = ["# BuzzWire Approved Posts", ""]
    for post in posts:
        lines.extend(
            [
                f"## {post['page_name']}: {post['viral_title']}",
                "",
                f"**Topic:** {post['topic_title']}",
                f"**Source:** {post.get('source_url') or 'Manual input'}",
                f"**Virality Score:** {post['virality_score']}",
                f"**Risk:** {post['risk_level'].title()}",
                "",
                "**Neutral Title:**",
                post["neutral_title"],
                "",
                "**Viral Title:**",
                post["viral_title"],
                "",
                "**Aggressive Title:**",
                post["aggressive_title"],
                "",
                "**Caption:**",
                post["caption"],
                "",
                "**Carousel:**",
            ]
        )
        lines.extend(f"- {line}" for line in post.get("carousel_text", []))
        lines.extend(
            [
                "",
                "**Visual Direction:**",
                post["visual_direction"],
                "",
                "**Suggested Image Keywords:**",
                ", ".join(post.get("suggested_image_keywords", [])),
                "",
                "**Risk Notes:**",
                post["risk_notes"],
                "",
                "---",
                "",
            ]
        )
    return "\n".join(lines)
