import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class VisibilityScore(Base):
    __tablename__ = "visibility_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_id = Column(
        UUID(as_uuid=True),
        ForeignKey("audits.id"),
        unique=True,
        nullable=False,
        index=True,
    )
    overall_score = Column(Integer, nullable=False)  # 0-100
    per_engine_scores = Column(JSONB, nullable=False)  # {"openai": {...}, "anthropic": {...}}
    mention_count = Column(Integer, nullable=False, default=0)
    query_mention_rate = Column(Numeric(5, 2), nullable=False)  # percentage of queries with mentions
    algorithm_version = Column(String, nullable=False, default="v2")
    confidence_level = Column(String, nullable=False, server_default="low")  # high/medium/low/not_measured
    engines_queried = Column(Integer, nullable=False, server_default="0")
    engines_skipped = Column(Integer, nullable=False, server_default="0")
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    audit = relationship("Audit", backref="visibility_score")
