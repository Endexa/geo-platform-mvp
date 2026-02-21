import uuid
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.profile import Profile
from app.core.security import SecurityManager
from loguru import logger


class AuthService:
    """Authentication business logic"""

    def __init__(self, db: Session):
        self.db = db

    def register(self, email: str, password: str, full_name: str | None = None) -> Profile:
        """Register a new user. Returns the created Profile."""
        # Check for duplicate email
        existing = self.db.query(Profile).filter(Profile.email == email).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email already exists"
            )

        # Create new profile
        user = Profile(
            id=uuid.uuid4(),
            email=email,
            password_hash=SecurityManager.hash_password(password),
            full_name=full_name,
            is_active=True,
        )

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        logger.info(f"User registered: {user.id} ({email})")
        return user

    def authenticate(self, email: str, password: str) -> Profile:
        """Authenticate a user by email/password. Returns the Profile on success."""
        user = self.db.query(Profile).filter(Profile.email == email).first()

        if not user or not SecurityManager.verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account deactivated"
            )

        logger.info(f"User authenticated: {user.id} ({email})")
        return user
