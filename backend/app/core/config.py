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

    # AI Provider Keys
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GEMINI_API_KEY: str = ""

    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_PRICE_PRO_MONTHLY: str = ""
    STRIPE_PRICE_PRO_YEARLY: str = ""
    STRIPE_PORTAL_CONFIG_ID: str = ""  # bpc_xxx from Dashboard (optional)
    FRONTEND_URL: str = "http://localhost:3000"

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

    # Query Generation (Phase 2)
    QUERY_GEN_MODEL: str = "gemini/gemini-2.5-flash"  # LLM model for query generation (configurable)
    QUERY_GEN_TEMPERATURE: float = 0.7  # Some creativity for diverse queries
    QUERY_GEN_MAX_CONTENT_WORDS: int = 2000  # Truncation limit for crawl content in LLM prompt

    # AI Engine Dispatch (Phase 3)
    PERPLEXITYAI_API_KEY: str = ""  # LiteLLM expects this exact env var name
    DISPATCH_MODEL_OPENAI: str = "gpt-4o-mini"
    DISPATCH_MODEL_ANTHROPIC: str = "anthropic/claude-haiku-4-5"
    DISPATCH_MODEL_PERPLEXITY: str = "perplexity/sonar"
    DISPATCH_MODEL_GEMINI: str = "gemini/gemini-2.5-flash"
    DISPATCH_TEMPERATURE: float = 0.0  # Reproducibility for Phase 4
    DISPATCH_TIMEOUT_SECONDS: int = 60  # Per-engine call timeout
    DISPATCH_MAX_WORKERS: int = 6  # ThreadPoolExecutor pool size
    PERPLEXITY_REQUEST_SURCHARGE: float = 0.005  # Per-request surcharge for Perplexity search fees

    # Mention Detection & Scoring (Phase 4)
    MENTION_FUZZY_THRESHOLD: int = 80  # RapidFuzz score threshold (0-100)
    MENTION_SHORT_NAME_THRESHOLD: int = 90  # Higher threshold for brand names < 4 chars
    MENTION_CONTEXT_WINDOW_CHARS: int = 200  # Character window for context extraction

    # Auto-Competitor Discovery (Phase 7)
    COMPETITOR_CRAWL_CAP: int = 5  # Max pages per competitor site
    COMPETITOR_MAX_COUNT: int = 5  # Max competitors to auto-crawl
    COMPETITOR_URL_RESOLVE_TIMEOUT: float = 5.0  # Timeout for URL resolution HTTP checks

    # Code Analysis (Phase 8)
    CODE_ANALYSIS_MODEL: str = "gemini/gemini-2.5-flash"  # Same cheap model used for chat
    CODE_ANALYSIS_MAX_UPLOAD_BYTES: int = 100 * 1024  # 100KB hard cap on uploaded text
    CODE_ANALYSIS_MAX_TOKENS_INPUT: int = 50000  # Truncate input before sending to LLM

    # Chat Assistant (Phase 6)
    CHAT_MODEL: str = "gemini/gemini-2.5-flash"  # Cheap model for chat
    CHAT_TEMPERATURE: float = 0.3  # Low temperature for factual, grounded answers
    CHAT_MAX_TOKENS: int = 1024  # Cap response length
    CHAT_MAX_HISTORY: int = 20  # Max messages in conversation context
    CHAT_MAX_CONTEXT_TOKENS: int = 3000  # Budget for system prompt

    # Site AI-Readiness Scoring (Phase 6)
    SCORING_CRAWL_CAP: int = 25  # Max pages per audit for scoring
    SCORING_STAGE_TIMEOUT_SECONDS: int = 600  # 10 min timeout for scoring stage
    GOOGLE_API_KEY: str = ""  # Optional, for PageSpeed Insights and Knowledge Graph

    # Outbound AI Rate Limits (Phase 1)
    OPENAI_RPM: int = 60
    ANTHROPIC_RPM: int = 60
    PERPLEXITY_RPM: int = 20
    GEMINI_RPM: int = 15
    OPENAI_MAX_CONCURRENT: int = 10
    ANTHROPIC_MAX_CONCURRENT: int = 10
    PERPLEXITY_MAX_CONCURRENT: int = 5
    GEMINI_MAX_CONCURRENT: int = 5

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
