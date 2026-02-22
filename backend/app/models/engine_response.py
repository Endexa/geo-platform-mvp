import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class EngineResponse(Base):
    __tablename__ = "engine_responses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_query_id = Column(
        UUID(as_uuid=True),
        ForeignKey("audit_queries.id"),
        nullable=False,
        index=True,
    )
    engine = Column(String, nullable=False)  # "openai", "anthropic", "perplexity"
    model_version = Column(String, nullable=False)  # actual model string from LiteLLM
    response_text = Column(Text, nullable=False)  # full AI response
    prompt_tokens = Column(Integer, nullable=False, default=0)
    completion_tokens = Column(Integer, nullable=False, default=0)
    cost_usd = Column(Numeric(10, 6), nullable=False, default=0)
    cached = Column(Boolean, default=False)
    citations = Column(JSONB, nullable=True)  # list of source URLs from Perplexity/inline
    error_message = Column(String, nullable=True)  # non-null if engine failed
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    audit_query = relationship("AuditQuery", back_populates="engine_responses")
