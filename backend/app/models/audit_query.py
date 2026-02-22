import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class AuditQuery(Base):
    __tablename__ = "audit_queries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_id = Column(
        UUID(as_uuid=True),
        ForeignKey("audits.id"),
        nullable=False,
        index=True,
    )
    category = Column(String, nullable=False)  # industry, brand_direct, comparison, problem, recommendation
    query_text = Column(String, nullable=False)
    sort_order = Column(Integer, default=0)
    is_custom = Column(Boolean, default=False)  # True for user-added queries
    is_editable = Column(Boolean, default=True)  # False for auto-generated queries after dispatch
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    audit = relationship("Audit", back_populates="queries")
    engine_responses = relationship(
        "EngineResponse", back_populates="audit_query", cascade="all, delete-orphan"
    )
