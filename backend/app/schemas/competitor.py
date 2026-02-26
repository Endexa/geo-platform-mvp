"""Pydantic schemas for competitor API responses.

Defines response models for the competitor leaderboard, competitor audit
summaries, and the combined leaderboard response.
"""

from pydantic import BaseModel, ConfigDict


class CompetitorLeaderboardEntry(BaseModel):
    """A single entity in the competitor leaderboard."""

    entity_name: str
    entity_type: str  # "ORG" or "PRODUCT"
    mention_count: int
    share_of_voice: float  # percentage, e.g., 37.5
    engines_mentioned_in: dict[str, int]  # engine name -> count
    queries_mentioned_in: list[str]  # query IDs as strings
    resolved_url: str | None
    is_crawled: bool
    is_user_brand: bool
    competitor_audit_id: str | None

    model_config = ConfigDict(from_attributes=True)


class CompetitorAuditSummary(BaseModel):
    """Summary of a competitor's crawl and scoring results."""

    id: str
    competitor_name: str
    competitor_url: str
    optimization_score: int | None
    crawlability_avg: int | None
    content_structure_avg: int | None
    structured_data_avg: int | None
    authority_avg: int | None
    pages_scored: int
    status: str
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class CompetitorLeaderboardResponse(BaseModel):
    """Full leaderboard response with entities and competitor audit data."""

    audit_id: str
    user_brand_name: str
    total_entities: int
    competitors: list[CompetitorLeaderboardEntry]
    competitor_audits: list[CompetitorAuditSummary]


class ScoreComparisonSite(BaseModel):
    """Score data for the user's audited site in a comparison."""

    name: str
    url: str
    optimization_score: int | None
    crawlability: int | None
    content_structure: int | None
    structured_data: int | None
    authority: int | None

    model_config = ConfigDict(from_attributes=True)


class ScoreComparisonCompetitor(BaseModel):
    """Score data for a competitor in a comparison."""

    name: str
    url: str
    optimization_score: int | None
    crawlability: int | None
    content_structure: int | None
    structured_data: int | None
    authority: int | None

    model_config = ConfigDict(from_attributes=True)


class ScoreComparisonResponse(BaseModel):
    """Side-by-side score comparison: user's site vs competitors."""

    site: ScoreComparisonSite
    competitors: list[ScoreComparisonCompetitor]
