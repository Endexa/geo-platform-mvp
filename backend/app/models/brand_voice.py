from sqlalchemy import Column, String, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
import uuid
from app.core.database import Base


class BrandVoiceConfig(Base):
    __tablename__ = "brand_voice_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    # Relationships
    organization = relationship("Organization", back_populates="brand_voice_configs")
    voice_vectors = relationship("VoiceVector", back_populates="config", cascade="all, delete-orphan")
    voice_rules = relationship("VoiceRule", back_populates="config", cascade="all, delete-orphan")


class VoiceVector(Base):
    __tablename__ = "voice_vectors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    config_id = Column(UUID(as_uuid=True), ForeignKey("brand_voice_configs.id"), nullable=False)
    content_chunk = Column(Text, nullable=False)
    embedding = Column(Vector(1536))  # OpenAI text-embedding-3-small dimension

    # Relationships
    config = relationship("BrandVoiceConfig", back_populates="voice_vectors")


class VoiceRule(Base):
    __tablename__ = "voice_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    config_id = Column(UUID(as_uuid=True), ForeignKey("brand_voice_configs.id"), nullable=False)
    rule_type = Column(String, nullable=False)  # 'forbidden_word', 'required_phrase', 'tone_directive'
    value = Column(Text, nullable=False)

    # Relationships
    config = relationship("BrandVoiceConfig", back_populates="voice_rules")
