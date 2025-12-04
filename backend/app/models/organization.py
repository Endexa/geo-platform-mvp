from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.core.database import Base


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    subscription_tier = Column(String, default="free")  # free, pro, enterprise
    stripe_customer_id = Column(String, nullable=True)

    # Relationships
    profiles = relationship("Profile", back_populates="organization")
    websites = relationship("Website", back_populates="organization")
    brand_voice_configs = relationship("BrandVoiceConfig", back_populates="organization")
