from sqlalchemy import Column, String, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.core.database import Base


class Website(Base):
    __tablename__ = "websites"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)  # Nullable for MVP
    domain = Column(String, nullable=False)
    sitemap_url = Column(String, nullable=True)
    last_crawled_at = Column(DateTime, nullable=True)

    # Relationships
    organization = relationship("Organization", back_populates="websites")
    analyses = relationship("Analysis", back_populates="website", cascade="all, delete-orphan")
