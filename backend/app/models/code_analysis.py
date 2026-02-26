"""SQLAlchemy models for the code analysis feature.

CodeAnalysis tracks a single upload-and-parse session (one per upload per audit).
CodeRecommendation stores structured findings extracted from AI tool output,
linked to both the code analysis session and the parent audit.
"""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class CodeAnalysis(Base):
    """Represents a code analysis session: one per AI tool output upload per audit."""

    __tablename__ = "code_analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_id = Column(
        UUID(as_uuid=True), ForeignKey("audits.id"), nullable=False, index=True
    )
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False, index=True
    )
    # Status lifecycle: pending -> parsing -> recommending -> completed / failed
    status = Column(String, nullable=False, default="pending")
    raw_output = Column(Text, nullable=False)
    raw_output_size_bytes = Column(Integer, nullable=False)
    detected_framework = Column(String, nullable=True)
    parsed_findings = Column(JSONB, nullable=True)
    prompt_categories_used = Column(JSONB, nullable=True)
    model_used = Column(String, nullable=True)
    error_message = Column(String, nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    audit = relationship("Audit", backref="code_analyses")
    recommendations = relationship(
        "CodeRecommendation", back_populates="code_analysis", cascade="all, delete-orphan"
    )


class CodeRecommendation(Base):
    """A single code-level recommendation extracted from AI tool output."""

    __tablename__ = "code_recommendations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code_analysis_id = Column(
        UUID(as_uuid=True),
        ForeignKey("code_analyses.id"),
        nullable=False,
        index=True,
    )
    audit_id = Column(
        UUID(as_uuid=True), ForeignKey("audits.id"), nullable=False, index=True
    )
    # Optional mapping to existing scoring criterion (e.g. "SD3", "C5")
    criterion_id = Column(String, nullable=True)
    category = Column(String, nullable=False)  # crawlability, content_structure, structured_data, authority
    severity = Column(String, nullable=False)  # high, medium, low
    finding = Column(Text, nullable=False)
    file_path = Column(String, nullable=True)
    suggestion = Column(Text, nullable=False)
    code_snippet = Column(Text, nullable=True)
    evidence = Column(Text, nullable=True)
    status = Column(String, nullable=False, server_default="open")  # open, done, dismissed
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    code_analysis = relationship("CodeAnalysis", back_populates="recommendations")
