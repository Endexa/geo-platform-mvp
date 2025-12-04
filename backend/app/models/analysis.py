from sqlalchemy import Column, String, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.core.database import Base


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    website_id = Column(UUID(as_uuid=True), ForeignKey("websites.id"), nullable=False)
    status = Column(String, default="pending")  # pending, processing, completed, failed
    geo_score = Column(Integer, nullable=True)  # 0-100
    visibility_score = Column(Integer, nullable=True)  # 0-100
    readability_score = Column(Integer, nullable=True)  # 0-100
    authority_score = Column(Integer, nullable=True)  # 0-100
    raw_data = Column(JSONB, nullable=True)  # Stores the raw crawler output
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    website = relationship("Website", back_populates="analyses")
    recommendations = relationship("Recommendation", back_populates="analysis", cascade="all, delete-orphan")
