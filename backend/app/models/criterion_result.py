import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class CriterionResult(Base):
    __tablename__ = "criterion_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    page_score_id = Column(
        UUID(as_uuid=True),
        ForeignKey("page_scores.id"),
        nullable=False,
        index=True,
    )
    criterion_id = Column(String, nullable=False)  # e.g. "C1", "CS3", "SD7"
    criterion_name = Column(String, nullable=False)
    category = Column(
        String, nullable=False
    )  # "crawlability", "content_structure", "structured_data", "authority"
    score = Column(Integer, nullable=False)
    max_score = Column(Integer, nullable=False, default=100)
    is_binary = Column(Boolean, nullable=False, default=False)
    human_summary = Column(Text, nullable=False)
    technical_detail = Column(Text, nullable=False)
    evidence = Column(JSONB, nullable=True)
    checked = Column(Boolean, nullable=False, default=True)

    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    page_score = relationship("PageScore", back_populates="criterion_results")
