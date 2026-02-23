"""Pydantic v2 schemas for brand CRUD operations."""

from datetime import datetime
from urllib.parse import urlparse
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


def normalize_domain(url: str) -> str:
    """Normalize a URL to its bare domain.

    Strips scheme, www. prefix, and lowercases.
    Used in brand creation AND audit auto-association for consistency.
    """
    parsed = urlparse(url)
    domain = parsed.netloc or parsed.path
    domain = domain.lower()
    if domain.startswith("www."):
        domain = domain[4:]
    # Strip port if present
    if ":" in domain:
        domain = domain.split(":")[0]
    return domain


class BrandCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    url: str
    description: str | None = None


class BrandUpdate(BaseModel):
    name: str | None = None
    url: str | None = None
    description: str | None = None


class BrandResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    url: str
    domain: str
    description: str | None
    created_at: datetime
    updated_at: datetime
    audit_count: int = 0


class BrandListResponse(BaseModel):
    brands: list[BrandResponse]
    total: int
