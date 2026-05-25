from __future__ import annotations

from pydantic import BaseModel, Field


class ManualTopic(BaseModel):
    title: str = Field(..., min_length=3)
    summary: str = ""
    source_url: str = ""
    niche_hint: str = ""


class ToneChange(BaseModel):
    tone: str = Field(..., min_length=3, max_length=80)


class ApprovalNote(BaseModel):
    notes: str = ""


class PostEdit(BaseModel):
    neutral_title: str | None = None
    viral_title: str | None = None
    aggressive_title: str | None = None
    caption: str | None = None
    visual_direction: str | None = None


class PageProfilePayload(BaseModel):
    page_name: str = Field(..., min_length=2, max_length=80)
    username: str = Field(default="", max_length=80)
    niche: str = ""
    audience: str = ""
    emotional_drivers: list[str] = Field(default_factory=list)
    allowed_topics: list[str] = Field(default_factory=list)
    blocked_topics: list[str] = Field(default_factory=list)
    preferred_sources: list[str] = Field(default_factory=list)
    country_focus: str = ""
    tone_rules: str = ""
    headline_style: str = ""
    caption_style: str = ""
    visual_style: str = ""
    risk_tolerance: str = "medium"
