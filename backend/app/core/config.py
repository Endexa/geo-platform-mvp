from pydantic_settings import BaseSettings
from typing import List
import os
import secrets


class Settings(BaseSettings):
    # App
    APP_NAME: str = "GEO Platform API"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Password Policy
    PASSWORD_MIN_LENGTH: int = 12
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_DIGITS: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = True

    # Database
    DATABASE_URL: str
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # Supabase (optional -- moving to self-managed auth)
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    SUPABASE_SERVICE_KEY: str = ""

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_MAX_CONNECTIONS: int = 50

    # OpenAI
    OPENAI_API_KEY: str
    ANTHROPIC_API_KEY: str = ""

    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # Jira
    JIRA_BASE_URL: str = ""
    JIRA_EMAIL: str = ""
    JIRA_API_TOKEN: str = ""

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_MAX_AGE: int = 3600

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_FREE_TIER: int = 3  # analyses per day
    RATE_LIMIT_PRO_TIER: int = 100
    RATE_LIMIT_ENTERPRISE_TIER: int = 1000
    RATE_LIMIT_WINDOW: int = 60  # seconds

    # Request Limits
    MAX_REQUEST_SIZE: int = 10 * 1024 * 1024  # 10MB
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB

    # Security Headers
    ENABLE_SECURITY_HEADERS: bool = True
    ENABLE_CSRF_PROTECTION: bool = True

    # Audit Logging
    ENABLE_AUDIT_LOGGING: bool = True
    LOG_LEVEL: str = "INFO"

    # IP Whitelist (for admin endpoints)
    WHITELISTED_IPS: List[str] = []

    # Monitoring
    SENTRY_DSN: str = ""
    ENABLE_METRICS: bool = True

    # Feature Flags
    ENABLE_RATE_LIMITING: bool = True
    ENABLE_API_KEYS: bool = True
    ENABLE_WEBHOOKS: bool = True

    # API Keys
    API_KEY_HEADER: str = "X-API-Key"
    API_KEY_EXPIRY_DAYS: int = 90

    # Session
    SESSION_COOKIE_SECURE: bool = True
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = "lax"

    # Encryption
    ENCRYPTION_KEY: str = ""  # For encrypting sensitive data at rest

    # Audit & Cost Controls (Phase 1)
    AUDIT_BUDGET_USD: float = 1.00  # Default per-audit budget cap
    AI_CACHE_TTL_SECONDS: int = 86400  # 24h cache TTL

    # Outbound AI Rate Limits (Phase 1)
    OPENAI_RPM: int = 60
    ANTHROPIC_RPM: int = 60
    PERPLEXITY_RPM: int = 20
    OPENAI_MAX_CONCURRENT: int = 10
    ANTHROPIC_MAX_CONCURRENT: int = 10
    PERPLEXITY_MAX_CONCURRENT: int = 5

    class Config:
        env_file = ".env"
        case_sensitive = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # L-30 fix: raise error in production if ENCRYPTION_KEY not set
        if self.ENVIRONMENT == "production" and not self.ENCRYPTION_KEY:
            raise ValueError("ENCRYPTION_KEY must be set in production")
        if not self.ENCRYPTION_KEY:
            self.ENCRYPTION_KEY = secrets.token_urlsafe(32)


settings = Settings()
