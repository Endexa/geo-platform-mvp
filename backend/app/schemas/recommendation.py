"""Pydantic schemas for recommendation API responses.

Defines response models for recommendation lists, status updates,
per-engine sentiment summaries, content gaps with mini briefs,
and the combined list responses.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class AuditRecommendationResponse(BaseModel):
    """A single audit recommendation with evidence and action steps."""

    id: str
    audit_id: str
    page_url: str | None
    criterion_id: str
    criterion_name: str
    category: str
    priority: str
    impact_label: str
    impact_pct: int | None
    user_score: int
    competitor_avg: int | None
    gap_score: int
    summary: str
    action_steps: list[str]
    code_snippet: str | None
    evidence_source: str
    recommendation_hash: str
    status: str

    model_config = ConfigDict(from_attributes=True)


class RecommendationStatusUpdate(BaseModel):
    """Request body for updating a recommendation's status."""

    status: Literal["open", "done", "dismissed"]


class RecommendationListResponse(BaseModel):
    """Paginated list of recommendations with summary statistics."""

    recommendations: list[AuditRecommendationResponse]
    total: int
    by_priority: dict[str, int]  # {"high": N, "medium": M, "low": K}
    progress: dict[str, int]  # {"done": N, "dismissed": M, "open": K, "total": T}


class SentimentSummaryResponse(BaseModel):
    """Per-engine sentiment breakdown for an audit."""

    engine_sentiments: dict[str, dict]
    # {engine: {positive: N, negative: N, neutral: N, total: N, dominant: str}}


class ContentGapResponse(BaseModel):
    """A single content gap with competitor data and mini brief."""

    query_id: str
    query_text: str
    competitors_mentioned: list[str]
    brief: dict  # {title: str, key_points: list[str], target_queries: list[str]}


class ContentGapListResponse(BaseModel):
    """List of content gaps with total count."""

    gaps: list[ContentGapResponse]
    total: int
