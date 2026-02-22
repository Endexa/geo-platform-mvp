import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class MentionSentiment(Base):
    __tablename__ = "mention_sentiments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_id = Column(
        UUID(as_uuid=True),
        ForeignKey("audits.id"),
        nullable=False,
        index=True,
    )
    brand_mention_id = Column(
        UUID(as_uuid=True),
        ForeignKey("brand_mentions.id"),
        nullable=False,
        unique=True,
    )
    engine = Column(
        String, nullable=False
    )  # "openai", "anthropic", "perplexity", "gemini"
    sentiment = Column(
        String, nullable=False
    )  # "positive", "negative", "neutral"
    confidence = Column(Integer, nullable=False)  # 0-100
    context_quote = Column(
        Text, nullable=False
    )  # copied from BrandMention for convenience
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    audit = relationship("Audit", backref="mention_sentiments")
