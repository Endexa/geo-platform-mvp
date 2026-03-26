"""
llms.txt Model — Stores llms.txt validation and generation results.

The llms.txt standard helps AI crawlers understand site structure.
"""

from sqlalchemy import Column, Integer, String, Boolean, JSON, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class LlmsTxtAnalysis(Base):
    """Stores llms.txt validation and generation results for a website."""

    __tablename__ = "llms_txt_analyses"

    id = Column(Integer, primary_key=True, index=True)
    audit_id = Column(Integer, ForeignKey("audits.id", ondelete="CASCADE"), nullable=False, index=True)
    website_url = Column(String(2048), nullable=False)

    # Validation results
    llms_txt_url = Column(String(2048), nullable=False)
    llms_txt_exists = Column(Boolean, nullable=False, default=False)
    format_valid = Column(Boolean, nullable=False, default=False)

    # Format checks
    has_title = Column(Boolean, nullable=False, default=False)
    has_description = Column(Boolean, nullable=False, default=False)
    has_sections = Column(Boolean, nullable=False, default=False)
    has_links = Column(Boolean, nullable=False, default=False)

    # Metrics
    section_count = Column(Integer, nullable=False, default=0)
    link_count = Column(Integer, nullable=False, default=0)

    # Existing content (if found)
    existing_content = Column(Text, nullable=True)

    # Issues and suggestions (stored as JSON arrays)
    issues = Column(JSON, nullable=True)  # ["Missing title", "No sections found"]
    suggestions = Column(JSON, nullable=True)  # ["Add more key pages", "Add contact section"]

    # llms-full.txt check
    llms_full_txt_exists = Column(Boolean, nullable=False, default=False)

    # Generated content
    generated_llmstxt = Column(Text, nullable=True)
    generated_llmstxt_full = Column(Text, nullable=True)
    pages_analyzed = Column(Integer, nullable=False, default=0)

    # Section breakdown (stored as JSON)
    sections = Column(JSON, nullable=True)  # {"Main Pages": 5, "Products & Services": 10, ...}

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    audit = relationship("Audit", back_populates="llms_txt_analyses")

    def __repr__(self):
        return f"<LlmsTxtAnalysis(id={self.id}, audit_id={self.audit_id}, exists={self.llms_txt_exists}, valid={self.format_valid})>"
