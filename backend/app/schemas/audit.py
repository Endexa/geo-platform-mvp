from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuditCreate(BaseModel):
    """Request schema for creating a new audit."""

    url: str


class EngineResponseSchema(BaseModel):
    """Response schema for an individual engine response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    engine: str
    model_version: str
    response_text: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    cached: bool
    error_message: Optional[str] = None
    created_at: datetime


class AuditQueryResponse(BaseModel):
    """Response schema for an individual audit query."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    category: str
    query_text: str
    sort_order: int
    engine_responses: list[EngineResponseSchema] = []


class DispatchSummary(BaseModel):
    """Summary of dispatch results for an audit."""

    total_queries: int
    total_responses: int
    total_failures: int
    engines_used: list[str]


class AuditResponse(BaseModel):
    """Response schema for audit listing / summary."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    url: str
    domain: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class AuditDetailResponse(AuditResponse):
    """Response schema for audit detail view (includes crawl data, queries, and dispatch summary)."""

    crawl_data: Optional[dict] = None
    queries: list[AuditQueryResponse] = []
    dispatch_summary: Optional[DispatchSummary] = None
