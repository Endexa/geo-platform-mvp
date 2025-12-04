"""
GEO Data Points Database Models

SQLAlchemy models for storing GEO analysis results.
"""

from sqlalchemy import Column, String, Float, DateTime, Text, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

Base = declarative_base()


class Analysis(Base):
    """
    Main analysis record for a website URL.

    Each analysis represents a complete GEO data points measurement run.
    """
    __tablename__ = "geo_analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_url = Column(String, nullable=False, index=True)
    status = Column(String, default="pending")  # pending, running, completed, failed
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    total_data_points = Column(Integer, default=0)
    successful_measurements = Column(Integer, default=0)
    failed_measurements = Column(Integer, default=0)
    average_score = Column(Float, nullable=True)

    # Relationship to results
    results = relationship("DataPointResult", back_populates="analysis", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Analysis {self.id} - {self.site_url} - {self.status}>"


class DataPointResult(Base):
    """
    Individual data point measurement result.

    Stores the score, comment, and metadata for each GEO data point.
    """
    __tablename__ = "geo_data_point_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id = Column(UUID(as_uuid=True), ForeignKey("geo_analyses.id"), nullable=False, index=True)

    # Data point identification
    data_point_name = Column(String, nullable=False, index=True)
    module = Column(String, nullable=False, index=True)  # WI, CNT, BV, SEO, UX, COMP, LEG
    priority = Column(String, nullable=False)  # High, Med, Low

    # Measurement results
    score = Column(Float, nullable=False)  # 0-100
    comment = Column(Text, nullable=False)

    # Metadata
    measurement_method = Column(String, nullable=True)
    automation_level = Column(String, nullable=True)  # Full, Semi
    execution_time_ms = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship to analysis
    analysis = relationship("Analysis", back_populates="results")

    def __repr__(self):
        return f"<DataPointResult {self.data_point_name} - Score: {self.score}>"
