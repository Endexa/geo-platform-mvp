import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class PageScore(Base):
    __tablename__ = "page_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_id = Column(
        UUID(as_uuid=True),
        ForeignKey("audits.id"),
        nullable=False,
        index=True,
    )
    page_url = Column(String, nullable=False)
    page_title = Column(String, nullable=True)
    crawl_data = Column(JSONB, nullable=True)  # Per-page crawl result

    # Category scores (0-100)
    crawlability_score = Column(Integer, nullable=True)
    content_structure_score = Column(Integer, nullable=True)
    structured_data_score = Column(Integer, nullable=True)
    authority_score = Column(Integer, nullable=True)
    overall_page_score = Column(Integer, nullable=True)  # Weighted combination

    # Discovery metadata
    internal_link_count = Column(Integer, nullable=False, default=0)
    was_scored = Column(
        Boolean, nullable=False, default=True
    )  # False = discovered but not scored due to cap

    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    audit = relationship("Audit", backref="page_scores")
    criterion_results = relationship(
        "CriterionResult",
        back_populates="page_score",
        cascade="all, delete-orphan",
    )
