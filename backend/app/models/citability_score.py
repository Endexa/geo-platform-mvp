"""
Citability Score Model — Stores AI citation readiness scores for content blocks.

Tracks how well content is optimized for AI citations based on:
- Answer Block Quality (30%)
- Self-Containment (25%)
- Structural Readability (20%)
- Statistical Density (15%)
- Uniqueness Signals (10%)
"""

from sqlalchemy import Column, Integer, String, Float, JSON, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class CitabilityScore(Base):
    """Stores citability analysis results for content blocks."""

    __tablename__ = "citability_scores"

    id = Column(Integer, primary_key=True, index=True)
    audit_id = Column(Integer, ForeignKey("audits.id", ondelete="CASCADE"), nullable=False, index=True)
    page_url = Column(String(2048), nullable=False)

    # Content block information
    heading = Column(String(500), nullable=True)
    content_preview = Column(Text, nullable=True)  # First 30 words
    word_count = Column(Integer, nullable=False)

    # Scores
    total_score = Column(Float, nullable=False)  # 0-100
    grade = Column(String(1), nullable=False)  # A, B, C, D, F
    label = Column(String(50), nullable=False)  # "Highly Citable", "Good Citability", etc.

    # Score breakdown (stored as JSON)
    breakdown = Column(JSON, nullable=False)  # {answer_block_quality: 25, self_containment: 20, ...}

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    audit = relationship("Audit", back_populates="citability_scores")

    def __repr__(self):
        return f"<CitabilityScore(id={self.id}, audit_id={self.audit_id}, grade={self.grade}, score={self.total_score})>"


class PageCitabilityAnalysis(Base):
    """Stores page-level citability metrics."""

    __tablename__ = "page_citability_analyses"

    id = Column(Integer, primary_key=True, index=True)
    audit_id = Column(Integer, ForeignKey("audits.id", ondelete="CASCADE"), nullable=False, index=True)
    page_url = Column(String(2048), nullable=False, unique=True)

    # Page-level metrics
    total_blocks_analyzed = Column(Integer, nullable=False)
    average_citability_score = Column(Float, nullable=False)
    optimal_length_passages = Column(Integer, nullable=False)  # Count of 134-167 word passages

    # Grade distribution (stored as JSON)
    grade_distribution = Column(JSON, nullable=False)  # {A: 2, B: 5, C: 10, D: 3, F: 1}

    # Top and bottom performing blocks (stored as JSON - array of CitabilityScore-like dicts)
    top_5_citable = Column(JSON, nullable=True)
    bottom_5_citable = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    audit = relationship("Audit", back_populates="page_citability_analyses")

    def __repr__(self):
        return f"<PageCitabilityAnalysis(id={self.id}, audit_id={self.audit_id}, avg_score={self.average_citability_score})>"
