import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class AuditStatus(str, enum.Enum):
    PENDING = "pending"
    CRAWLING = "crawling"
    GENERATING_QUERIES = "generating_queries"
    DISPATCHING = "dispatching"
    ANALYZING = "analyzing"
    SCORING = "scoring"
    DISCOVERING_COMPETITORS = "discovering_competitors"
    RECOMMENDING = "recommending"
    COMPLETED = "completed"
    FAILED = "failed"


class Audit(Base):
    __tablename__ = "audits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False
    )
    url = Column(String, nullable=False)
    domain = Column(String, nullable=False)
    status = Column(String, default=AuditStatus.PENDING, nullable=False)
    crawl_data = Column(JSONB, nullable=True)
    error_message = Column(String, nullable=True)
    optimization_score = Column(Integer, nullable=True)  # Final 0-100 score after scoring
    vertical = Column(String, nullable=True)  # Detected site vertical (saas, ecommerce, etc.)
    content_gaps = Column(JSONB, nullable=True)  # List of content gap dicts from gap analysis
    brand_id = Column(
        UUID(as_uuid=True), ForeignKey("brands.id"), nullable=True, index=True
    )
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    queries = relationship(
        "AuditQuery", back_populates="audit", cascade="all, delete-orphan"
    )
    cost_entries = relationship(
        "AuditCostLedger",
        backref="audit",
        foreign_keys="AuditCostLedger.audit_id",
    )
    brand = relationship("Brand", back_populates="audits")
