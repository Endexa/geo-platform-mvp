from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(UUID(as_uuid=True), primary_key=True)  # Links to Supabase auth.users
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    full_name = Column(String, nullable=True)
    role = Column(String, default="member")  # member, admin, owner

    # Relationships
    organization = relationship("Organization", back_populates="profiles")
