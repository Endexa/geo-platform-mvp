"""Pydantic schemas for dashboard API responses.

Defines response models for the dashboard overview, audit history,
competitive position, and recommendation progress.
"""

from pydantic import BaseModel, ConfigDict


class TopIssueSchema(BaseModel):
    """A high-priority recommendation displayed as a top issue."""

    id: str
    page_url: str | None
    criterion_id: str
    criterion_name: str
    category: str
    priority: str
    impact_label: str
    summary: str
    gap_score: int

    model_config = ConfigDict(from_attributes=True)


class CompetitorScoresSchema(BaseModel):
    """Score breakdown for a competitor across all dimensions."""

    name: str
    share_of_voice: float
    scores: dict[str, float]  # visibility, optimization, crawlability, content, schema, authority


class CompetitivePositionSchema(BaseModel):
    """User vs competitors score comparison for radar chart."""

    user_scores: dict[str, float]  # visibility, optimization, crawlability, content, schema, authority
    competitors: list[CompetitorScoresSchema]


class RecommendationProgressSchema(BaseModel):
    """Progress tracking for recommendations."""

    done: int
    dismissed: int
    open: int
    total: int


class AuditHistoryEntry(BaseModel):
    """A single audit data point for trend charts."""

    audit_id: str
    date: str
    visibility_score: int
    optimization_score: int
    combined_score: int
    mention_count: int
    per_engine_scores: dict[str, int] = {}
    crawlability_avg: int = 0
    content_structure_avg: int = 0
    structured_data_avg: int = 0
    authority_avg: int = 0


class AuditHistoryResponse(BaseModel):
    """Audit history for trend visualization."""

    domain: str
    entries: list[AuditHistoryEntry]
    total: int


class DashboardOverviewResponse(BaseModel):
    """Complete dashboard overview in a single response."""

    audit_id: str
    domain: str
    url: str
    completed_at: str | None
    combined_geo_score: int
    visibility_score: int
    optimization_score: int
    per_engine_scores: dict[str, int]
    mention_count: int
    query_mention_rate: float
    top_issues: list[TopIssueSchema]
    competitive_position: CompetitivePositionSchema
    recommendation_progress: RecommendationProgressSchema
