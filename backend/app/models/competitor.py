import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class DiscoveredCompetitor(Base):
    __tablename__ = "discovered_competitors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_id = Column(
        UUID(as_uuid=True),
        ForeignKey("audits.id"),
        nullable=False,
        index=True,
    )
    entity_name = Column(String, nullable=False)  # canonical name from NER
    entity_type = Column(String, nullable=False)  # "ORG" or "PRODUCT"
    mention_count = Column(Integer, nullable=False)  # total mentions across all responses
    share_of_voice = Column(Numeric(5, 1), nullable=False)  # percentage
    engines_mentioned_in = Column(JSONB, nullable=True)  # {"openai": 5, "anthropic": 3, ...}
    queries_mentioned_in = Column(JSONB, nullable=True)  # list of query_ids where entity appeared
    resolved_url = Column(String, nullable=True)  # resolved website URL
    is_crawled = Column(Boolean, default=False)
    is_user_brand = Column(Boolean, default=False)  # True if this is the audited brand
    competitor_audit_id = Column(
        UUID(as_uuid=True),
        ForeignKey("competitor_audits.id"),
        nullable=True,
    )  # set after crawl
    competitor_brand_id = Column(
        UUID(as_uuid=True),
        ForeignKey("brands.id"),
        nullable=True,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    audit = relationship("Audit", backref="discovered_competitors")
    competitor_brand = relationship("Brand", backref="competitor_appearances")


class CompetitorAudit(Base):
    __tablename__ = "competitor_audits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_audit_id = Column(
        UUID(as_uuid=True),
        ForeignKey("audits.id"),
        nullable=False,
        index=True,
    )
    competitor_name = Column(String, nullable=False)
    competitor_url = Column(String, nullable=False)
    crawl_data = Column(JSONB, nullable=True)
    optimization_score = Column(Integer, nullable=True)
    crawlability_avg = Column(Integer, nullable=True)
    content_structure_avg = Column(Integer, nullable=True)
    structured_data_avg = Column(Integer, nullable=True)
    authority_avg = Column(Integer, nullable=True)
    pages_scored = Column(Integer, default=0)
    status = Column(
        String, default="pending"
    )  # pending/crawling/scoring/completed/failed
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    parent_audit = relationship("Audit", backref="competitor_audits")
