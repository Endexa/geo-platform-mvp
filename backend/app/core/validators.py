from pydantic import BaseModel, validator, Field, HttpUrl
from typing import Optional, List
import re
from urllib.parse import urlparse
from loguru import logger


class SecureBaseModel(BaseModel):
    """Base model with security-focused validation"""

    class Config:
        # Prevent extra fields
        extra = "forbid"
        # Validate on assignment
        validate_assignment = True
        # Use enum values
        use_enum_values = True


class URLValidator:
    """Validate and sanitize URLs"""

    ALLOWED_SCHEMES = ["http", "https"]
    BLOCKED_DOMAINS = [
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "169.254",  # Link-local
        "10.",      # Private network
        "172.16",   # Private network
        "192.168"   # Private network
    ]

    @staticmethod
    def validate_url(url: str) -> str:
        """Validate URL against security rules"""

        try:
            parsed = urlparse(url)

            # Check scheme
            if parsed.scheme not in URLValidator.ALLOWED_SCHEMES:
                raise ValueError(f"URL scheme must be one of {URLValidator.ALLOWED_SCHEMES}")

            # Check for blocked domains (SSRF protection)
            domain = parsed.netloc.lower()

            for blocked in URLValidator.BLOCKED_DOMAINS:
                if blocked in domain:
                    raise ValueError("Access to internal/private networks is not allowed")

            # Check URL length
            if len(url) > 2048:
                raise ValueError("URL too long")

            # Check for suspicious patterns
            if any(pattern in url.lower() for pattern in ["javascript:", "data:", "file:"]):
                raise ValueError("Suspicious URL pattern detected")

            return url

        except Exception as e:
            logger.warning(f"URL validation failed: {str(e)}")
            raise ValueError(f"Invalid URL: {str(e)}")


class StringSanitizer:
    """Sanitize strings to prevent injection attacks"""

    # Patterns to detect potential attacks
    SQL_INJECTION_PATTERNS = [
        r"(\bor\b|\band\b).*=",
        r"union\s+select",
        r"drop\s+table",
        r"insert\s+into",
        r"delete\s+from",
        r"update\s+.*set",
        r"exec\s*\(",
        r"javascript:",
        r"<script",
    ]

    XSS_PATTERNS = [
        r"<script",
        r"javascript:",
        r"onerror\s*=",
        r"onload\s*=",
        r"<iframe",
    ]

    @staticmethod
    def sanitize(text: str, max_length: int = 10000) -> str:
        """Sanitize input string"""

        if not text:
            return text

        # Check length
        if len(text) > max_length:
            raise ValueError(f"Input too long. Maximum {max_length} characters allowed")

        # Check for SQL injection patterns
        for pattern in StringSanitizer.SQL_INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                logger.warning(f"Potential SQL injection detected: {pattern}")
                raise ValueError("Invalid input detected")

        # Check for XSS patterns
        for pattern in StringSanitizer.XSS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                logger.warning(f"Potential XSS detected: {pattern}")
                raise ValueError("Invalid input detected")

        # Remove null bytes
        text = text.replace("\x00", "")

        return text.strip()


class KeywordValidator:
    """Validate keyword inputs"""

    @staticmethod
    def validate_keywords(keywords: List[str]) -> List[str]:
        """Validate and sanitize keyword list"""

        if not keywords:
            return []

        if len(keywords) > 50:
            raise ValueError("Maximum 50 keywords allowed")

        validated = []
        for keyword in keywords:
            # Sanitize each keyword
            clean_keyword = StringSanitizer.sanitize(keyword, max_length=100)

            # Check keyword format
            if not clean_keyword or len(clean_keyword) < 2:
                continue

            # Check for suspicious patterns
            if not re.match(r'^[\w\s\-\.]+$', clean_keyword):
                logger.warning(f"Invalid keyword format: {clean_keyword}")
                continue

            validated.append(clean_keyword)

        return validated


class EmailValidator:
    """Validate email addresses"""

    EMAIL_REGEX = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )

    @staticmethod
    def validate(email: str) -> str:
        """Validate email format"""

        email = email.strip().lower()

        if not EmailValidator.EMAIL_REGEX.match(email):
            raise ValueError("Invalid email format")

        if len(email) > 254:  # RFC 5321
            raise ValueError("Email too long")

        return email


# Pydantic models with enhanced validation

class SecureAnalyzeRequest(SecureBaseModel):
    """Secure request model for analysis"""

    url: str = Field(..., min_length=10, max_length=2048)
    keywords: List[str] = Field(default=[], max_items=50)

    @validator('url')
    def validate_url(cls, v):
        return URLValidator.validate_url(v)

    @validator('keywords')
    def validate_keywords(cls, v):
        return KeywordValidator.validate_keywords(v)


class SecureTextInput(SecureBaseModel):
    """Secure model for text inputs"""

    text: str = Field(..., min_length=1, max_length=50000)

    @validator('text')
    def sanitize_text(cls, v):
        return StringSanitizer.sanitize(v)


class SecureBrandVoiceCheck(SecureBaseModel):
    """Secure request for brand voice checking"""

    text: str = Field(..., min_length=10, max_length=10000)
    config_id: str = Field(..., pattern=r'^[a-f0-9-]{36}$')  # UUID format

    @validator('text')
    def sanitize_text(cls, v):
        return StringSanitizer.sanitize(v, max_length=10000)


class SecureJiraRequest(SecureBaseModel):
    """Secure request for Jira integration"""

    recommendation_id: str = Field(..., pattern=r'^[a-f0-9-]{36}$')
    project_key: str = Field(..., min_length=2, max_length=10, pattern=r'^[A-Z]+$')

    @validator('project_key')
    def validate_project_key(cls, v):
        # Jira project keys are uppercase letters only
        if not v.isupper() or not v.isalpha():
            raise ValueError("Invalid Jira project key format")
        return v


class SecureAPIKeyRequest(SecureBaseModel):
    """Secure request for API key operations"""

    name: str = Field(..., min_length=3, max_length=100)
    permissions: List[str] = Field(default=["read"], max_items=20)

    @validator('name')
    def sanitize_name(cls, v):
        return StringSanitizer.sanitize(v, max_length=100)

    @validator('permissions')
    def validate_permissions(cls, v):
        allowed_permissions = [
            "read", "write", "delete", "admin",
            "analysis:create", "analysis:read",
            "optimization:read", "voice:read", "voice:write"
        ]

        for perm in v:
            if perm not in allowed_permissions:
                raise ValueError(f"Invalid permission: {perm}")

        return list(set(v))  # Remove duplicates


class PasswordValidator:
    """Password strength validator"""

    @staticmethod
    def validate(password: str) -> str:
        """Validate password strength"""

        if len(password) < 12:
            raise ValueError("Password must be at least 12 characters long")

        if len(password) > 128:
            raise ValueError("Password too long")

        # Check for required character types
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)

        if not (has_upper and has_lower and has_digit and has_special):
            raise ValueError(
                "Password must contain uppercase, lowercase, digit, and special character"
            )

        # Check for common passwords (simplified check)
        common_passwords = ["Password123!", "Admin123!", "Welcome123!"]
        if password in common_passwords:
            raise ValueError("Password is too common")

        return password


class FileUploadValidator:
    """Validate file uploads"""

    ALLOWED_EXTENSIONS = [".txt", ".pdf", ".doc", ".docx"]
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

    @staticmethod
    def validate(filename: str, file_size: int) -> None:
        """Validate file upload"""

        # Check file size
        if file_size > FileUploadValidator.MAX_FILE_SIZE:
            raise ValueError(f"File too large. Maximum size: {FileUploadValidator.MAX_FILE_SIZE / 1024 / 1024}MB")

        # Check extension
        if not any(filename.lower().endswith(ext) for ext in FileUploadValidator.ALLOWED_EXTENSIONS):
            raise ValueError(f"File type not allowed. Allowed: {FileUploadValidator.ALLOWED_EXTENSIONS}")

        # Check for path traversal
        if ".." in filename or "/" in filename or "\\" in filename:
            raise ValueError("Invalid filename")

        # Check filename length
        if len(filename) > 255:
            raise ValueError("Filename too long")
