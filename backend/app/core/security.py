from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import secrets
import hashlib
import hmac
from app.core.config import settings
from app.core.database import get_db
from app.models import Profile, Organization
from loguru import logger

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Bearer token
security = HTTPBearer()


class SecurityManager:
    """Centralized security manager for authentication and authorization"""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt"""
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against a hash"""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        })

        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt

    @staticmethod
    def create_refresh_token(data: dict) -> str:
        """Create JWT refresh token (longer lived)"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=7)

        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        })

        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt

    @staticmethod
    def verify_token(token: str) -> Dict[str, Any]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            return payload
        except JWTError as e:
            logger.warning(f"Token verification failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

    @staticmethod
    def generate_api_key() -> tuple[str, str]:
        """Generate API key and its hash"""
        api_key = secrets.token_urlsafe(32)
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        return api_key, api_key_hash

    @staticmethod
    def verify_api_key(api_key: str, stored_hash: str) -> bool:
        """Verify API key against stored hash"""
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        return hmac.compare_digest(api_key_hash, stored_hash)

    @staticmethod
    def sign_request(payload: str, secret: str) -> str:
        """Sign a request payload"""
        return hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()

    @staticmethod
    def verify_signature(payload: str, signature: str, secret: str) -> bool:
        """Verify request signature"""
        expected_signature = SecurityManager.sign_request(payload, secret)
        return hmac.compare_digest(signature, expected_signature)


# Dependency for getting current user
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Profile:
    """Get current authenticated user from JWT token"""

    token = credentials.credentials
    payload = SecurityManager.verify_token(token)

    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )

    # Get user from database
    user = db.query(Profile).filter(Profile.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    # Log access for audit
    logger.info(f"User {user_id} authenticated successfully")

    return user


async def get_current_active_user(
    current_user: Profile = Depends(get_current_user)
) -> Profile:
    """Get current active user (add additional checks if needed)"""
    # Add additional checks here (e.g., is_active, is_verified, etc.)
    return current_user


class RoleChecker:
    """Dependency for role-based access control"""

    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: Profile = Depends(get_current_user)) -> bool:
        if current_user.role not in self.allowed_roles:
            logger.warning(f"User {current_user.id} attempted unauthorized access. Role: {current_user.role}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return True


class OrganizationChecker:
    """Dependency to check organization access"""

    def __init__(self, required_tier: str = None):
        self.required_tier = required_tier

    def __call__(
        self,
        current_user: Profile = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> Organization:

        if not current_user.org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User not associated with any organization"
            )

        org = db.query(Organization).filter(Organization.id == current_user.org_id).first()

        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )

        # Check subscription tier if required
        if self.required_tier:
            tier_hierarchy = ["free", "pro", "enterprise"]
            required_level = tier_hierarchy.index(self.required_tier)
            current_level = tier_hierarchy.index(org.subscription_tier)

            if current_level < required_level:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail=f"This feature requires {self.required_tier} tier subscription"
                )

        return org


def verify_api_key_dependency(request: Request, db: Session = Depends(get_db)):
    """Verify API key from header"""
    api_key = request.headers.get("X-API-Key")

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )

    # Here you would check against stored API keys in database
    # For now, we'll implement a basic check
    # In production, store hashed API keys in a separate table

    logger.info(f"API key authentication attempted from {request.client.host}")

    # TODO: Implement actual API key verification
    # api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    # Check against database

    return True


# Export commonly used dependencies
require_admin = RoleChecker(["admin", "owner"])
require_pro = OrganizationChecker(required_tier="pro")
require_enterprise = OrganizationChecker(required_tier="enterprise")
