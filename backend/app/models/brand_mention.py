import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class BrandMention(Base):
    __tablename__ = "brand_mentions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    engine_response_id = Column(
        UUID(as_uuid=True),
        ForeignKey("engine_responses.id"),
        nullable=False,
        index=True,
    )
    matched_text = Column(String, nullable=False)
    match_type = Column(String, nullable=False)  # "exact" or "fuzzy"
    confidence = Column(Integer, nullable=False)  # 0-100
    char_offset = Column(Integer, nullable=False)
    context_quote = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    engine_response = relationship("EngineResponse", backref="mentions")
