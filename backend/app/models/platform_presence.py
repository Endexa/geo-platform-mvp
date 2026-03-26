"""
Platform Presence Model — Stores brand presence across AI-cited platforms.

Tracks brand visibility on:
- YouTube (0.737 correlation with AI citations - HIGHEST)
- Reddit (high correlation)
- Wikipedia (high correlation)
- LinkedIn (moderate correlation)
- Other platforms (Quora, Stack Overflow, GitHub, etc.)
"""

from sqlalchemy import Column, Integer, String, Boolean, JSON, ForeignKey, DateTime, Text, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class PlatformPresence(Base):
    """Stores brand presence data for a single platform."""

    __tablename__ = "platform_presences"

    id = Column(Integer, primary_key=True, index=True)
    brand_scan_id = Column(Integer, ForeignKey("brand_scans.id", ondelete="CASCADE"), nullable=False, index=True)

    # Platform identification
    platform_name = Column(String(100), nullable=False)  # "YouTube", "Reddit", "Wikipedia", etc.
    correlation = Column(Float, nullable=True)  # 0.737 for YouTube, null for others
    weight = Column(String(10), nullable=True)  # "25%", "20%", etc.

    # Presence indicators (platform-specific)
    has_official_presence = Column(Boolean, nullable=False, default=False)  # Channel, subreddit, page, etc.
    has_mentions = Column(Boolean, nullable=False, default=False)  # Mentioned in discussions/videos/articles

    # Search URL
    search_url = Column(String(2048), nullable=False)

    # Platform-specific data (stored as JSON)
    # For Wikipedia: {has_wikipedia_page: true, has_wikidata_entry: true, wikidata_id: "Q123", ...}
    # For others: placeholder for future API integration
    platform_data = Column(JSON, nullable=True)

    # Check instructions (for manual verification)
    check_instructions = Column(JSON, nullable=True)  # ["Check if brand has official channel", ...]

    # Recommendations (stored as JSON)
    recommendations = Column(JSON, nullable=False)  # ["Create YouTube channel", "Post educational content", ...]

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    brand_scan = relationship("BrandScan", back_populates="platform_presences")

    def __repr__(self):
        return f"<PlatformPresence(id={self.id}, platform={self.platform_name}, has_presence={self.has_official_presence})>"


class BrandScan(Base):
    """Stores complete brand mention scan results across all platforms."""

    __tablename__ = "brand_scans"

    id = Column(Integer, primary_key=True, index=True)
    audit_id = Column(Integer, ForeignKey("audits.id", ondelete="CASCADE"), nullable=False, index=True)

    # Brand information
    brand_name = Column(String(255), nullable=False)
    domain = Column(String(500), nullable=True)

    # Analysis metadata
    analysis_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Key insight
    key_insight = Column(Text, nullable=False, default="Brand mentions correlate 3x more strongly with AI visibility than backlinks (Ahrefs Dec 2025, 75K brands)")

    # Overall recommendations (stored as JSON)
    overall_recommendations = Column(JSON, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    audit = relationship("Audit", back_populates="brand_scans")
    platform_presences = relationship("PlatformPresence", back_populates="brand_scan", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<BrandScan(id={self.id}, audit_id={self.audit_id}, brand={self.brand_name})>"
