from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import SecurityManager, get_current_active_user
from app.models.profile import Profile
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, UserResponse
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/register", response_model=TokenResponse)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user and return an access token."""
    service = AuthService(db)
    user = service.register(
        email=request.email,
        password=request.password,
        full_name=request.full_name,
    )

    access_token = SecurityManager.create_access_token(data={"sub": str(user.id)})

    return TokenResponse(access_token=access_token)


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate user and return access + refresh tokens."""
    service = AuthService(db)
    user = service.authenticate(email=request.email, password=request.password)

    access_token = SecurityManager.create_access_token(data={"sub": str(user.id)})
    refresh_token = SecurityManager.create_refresh_token(data={"sub": str(user.id)})

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.get("/me", response_model=UserResponse)
def get_me(current_user: Profile = Depends(get_current_active_user)):
    """Return current authenticated user info."""
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
    )
