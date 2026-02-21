import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class AuditCostLedger(Base):
    __tablename__ = "audit_cost_ledger"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # FK to audits table will be added in Phase 2 when the audit model is created
    audit_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    engine = Column(String, nullable=False)  # "openai", "anthropic", "perplexity"
    model = Column(String, nullable=False)  # "gpt-4o", "claude-sonnet-4", "sonar-pro"
    prompt_tokens = Column(Integer, nullable=False)
    completion_tokens = Column(Integer, nullable=False)
    cost_usd = Column(Numeric(10, 6), nullable=False)  # 6 decimal places for sub-cent costs
    cached = Column(Boolean, default=False)  # whether this was a cache hit (cost=0)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
