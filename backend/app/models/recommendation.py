from sqlalchemy import Column, String, Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.core.database import Base


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id = Column(UUID(as_uuid=True), ForeignKey("analyses.id"), nullable=False)
    category = Column(String, nullable=False)  # 'content', 'technical', 'metadata'
    severity = Column(String, nullable=False)  # 'high', 'medium', 'low'
    issue = Column(Text, nullable=False)
    action_plan = Column(Text, nullable=False)  # The LLM generated advice
    impact_score = Column(String, nullable=True)  # e.g., '+15pts', '+20pts'
    implemented = Column(Boolean, default=False)
    jira_ticket_id = Column(String, nullable=True)

    # Relationships
    analysis = relationship("Analysis", back_populates="recommendations")
