import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class AuditRecommendation(Base):
    __tablename__ = "audit_recommendations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_id = Column(
        UUID(as_uuid=True),
        ForeignKey("audits.id"),
        nullable=False,
        index=True,
    )
    page_url = Column(String, nullable=True)  # None = site-wide recommendation
    criterion_id = Column(String, nullable=False)  # e.g. "SD7", "CS1", "SENTIMENT"
    criterion_name = Column(String, nullable=False)
    category = Column(
        String, nullable=False
    )  # "crawlability", "content_structure", "structured_data", "authority", "sentiment"
    priority = Column(String, nullable=False)  # "high", "medium", "low"
    impact_label = Column(String, nullable=False)  # e.g. "3.2x citation rate"
    impact_pct = Column(
        Integer, nullable=True
    )  # e.g. 320 means 3.2x (stored as int * 100)
    user_score = Column(Integer, nullable=False)  # 0-100
    competitor_avg = Column(
        Integer, nullable=True
    )  # from CompetitorAudit, None if no competitor data
    gap_score = Column(
        Integer, nullable=False
    )  # competitor_avg - user_score or benchmark - user_score
    summary = Column(Text, nullable=False)  # user-facing one-liner
    action_steps = Column(
        JSONB, nullable=False, server_default="[]"
    )  # list of step strings
    code_snippet = Column(
        Text, nullable=True
    )  # JSON-LD, robots.txt, etc. for expanded view
    evidence_source = Column(
        String, nullable=False
    )  # "BrightEdge 2024", "Princeton GEO paper"
    recommendation_hash = Column(
        String(16), nullable=False, index=True
    )  # SHA-256 truncated for cross-audit tracking
    status = Column(
        String, nullable=False, default="open"
    )  # "open", "done", "dismissed"
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    audit = relationship("Audit", backref="recommendations")
