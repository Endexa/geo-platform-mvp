from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuditCreate(BaseModel):
    """Request schema for creating a new audit."""

    url: str


class AuditQueryResponse(BaseModel):
    """Response schema for an individual audit query."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    category: str
    query_text: str
    sort_order: int


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
    """Response schema for audit detail view (includes crawl data and queries)."""

    crawl_data: Optional[dict] = None
    queries: list[AuditQueryResponse] = []
