"""Brand model for multi-brand management.

A Brand represents a customer's brand, identified by a normalized domain.
Audits are automatically associated with brands by domain matching.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Brand(Base):
    __tablename__ = "brands"
    __table_args__ = (
        UniqueConstraint("user_id", "domain", name="uq_brands_user_domain"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False, index=True
    )
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    domain = Column(String, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user = relationship("Profile", backref="brands")
    audits = relationship(
        "Audit", back_populates="brand", order_by="Audit.created_at.desc()"
    )
